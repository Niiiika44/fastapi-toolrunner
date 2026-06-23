import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    NotEnoughPermissionsError,
)
from app.core.exceptions import DomainError
from app.memory_allocator.exceptions import (
    EmptyFileError,
    InvalidUploadError,
    ParsingError,
    PlatformExtractionError,
    TestNotFoundError,
)
from app.users.exceptions import (
    EmailDomainNotAllowedError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)


DOMAIN_ERROR_STATUS: dict[int, tuple[type[DomainError], ...]] = {
    status.HTTP_400_BAD_REQUEST: (
        EmailDomainNotAllowedError,
        InvalidPasswordError,
        EmptyFileError,
        InvalidUploadError,
        ParsingError,
        PlatformExtractionError,
    ),
    status.HTTP_401_UNAUTHORIZED: (
        InvalidCredentialsError,
        InvalidTokenError,
    ),
    status.HTTP_403_FORBIDDEN: (
        NotEnoughPermissionsError,
    ),
    status.HTTP_404_NOT_FOUND: (
        UserNotFoundError,
        TestNotFoundError,
    ),
    status.HTTP_409_CONFLICT: (
        UserAlreadyExistsError,
    ),
}


def _build_status_map(
        grouped: dict[int, tuple[type[DomainError], ...]],
) -> dict[type[DomainError], int]:
    """Разворачивает группировку по коду в плоский lookup {исключение: код}."""
    flat: dict[type[DomainError], int] = {}
    for code, exceptions in grouped.items():
        for exc in exceptions:
            if exc in flat:
                raise RuntimeError(f"{exc.__name__} mapped to two statuses")
            flat[exc] = code
    return flat


EXCEPTION_STATUS_MAP: dict[type[DomainError], int] = _build_status_map(DOMAIN_ERROR_STATUS)


def _resolve_status(exc: DomainError) -> int:
    for cls in type(exc).__mro__:
        if cls in EXCEPTION_STATUS_MAP:
            return EXCEPTION_STATUS_MAP[cls]
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _log_error(request: Request, status_code: int, error_type: str, message: str) -> None:
    level = logging.ERROR if status_code >= 500 else logging.WARNING
    logger.log(level, "Request error", extra={
        "event": "request_error",
        "error_type": error_type,
        "status_code": status_code,
        "detail": message,
        "path": request.url.path,
        "method": request.method,
    })


def _error_response(
        status_code: int,
        message: str,
        headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message}},
        headers=headers,
    )


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    status_code = _resolve_status(exc)
    _log_error(request, status_code, type(exc).__name__, exc.message)
    return _error_response(status_code, exc.message)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    message = "; ".join(
        f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
        for err in exc.errors()
    ) or "Validation error"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    _log_error(request, status_code, type(exc).__name__, message)
    return _error_response(status_code, message)


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    _log_error(request, exc.status_code, type(exc).__name__, message)
    return _error_response(exc.status_code, message, headers=exc.headers)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.error("Unhandled error", exc_info=exc, extra={
        "event": "unhandled_error",
        "error_type": type(exc).__name__,
        "status_code": status_code,
        "path": request.url.path,
        "method": request.method,
    })
    return _error_response(status_code, "Internal Server Error")


def create_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики всех возможных ошибок."""
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
