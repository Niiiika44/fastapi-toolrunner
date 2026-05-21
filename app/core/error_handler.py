from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import DomainError
from app.core.error_mapping import EXCEPTION_STATUS_MAP


def resolve_status(exc: DomainError) -> int:
    for c in type(exc).__mro__:
        if c in EXCEPTION_STATUS_MAP:
            return EXCEPTION_STATUS_MAP[c]
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    status_code = resolve_status(exc=exc)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": exc.message,
            }
        }
    )
