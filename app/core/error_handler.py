import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.error_mapping import EXCEPTION_STATUS_MAP
from app.core.exceptions import DomainError

logger = logging.getLogger(__name__)


def resolve_status(exc: DomainError) -> int:
    for c in type(exc).__mro__:
        if c in EXCEPTION_STATUS_MAP:
            return EXCEPTION_STATUS_MAP[c]
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    status_code = resolve_status(exc=exc)
    level = logging.ERROR if status_code >= 500 else logging.WARNING
    logger.log(level, "Domain error", extra={
        "event": "domain_error",
        "error_type": type(exc).__name__,
        "status_code": status_code,
        "detail": exc.message,
        "path": request.url.path,
        "method": request.method,
    })
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": exc.message,
            }
        }
    )
