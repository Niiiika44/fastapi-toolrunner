from fastapi import status

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


EXCEPTION_STATUS_MAP: dict[type[DomainError], int] = {
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
    EmailDomainNotAllowedError: status.HTTP_400_BAD_REQUEST,
    UserAlreadyExistsError: status.HTTP_409_CONFLICT,
    InvalidPasswordError: status.HTTP_400_BAD_REQUEST,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidTokenError: status.HTTP_401_UNAUTHORIZED,
    NotEnoughPermissionsError: status.HTTP_403_FORBIDDEN,
    EmptyFileError: status.HTTP_400_BAD_REQUEST,
    InvalidUploadError: status.HTTP_400_BAD_REQUEST,
    ParsingError: status.HTTP_400_BAD_REQUEST,
    TestNotFoundError: status.HTTP_404_NOT_FOUND,
    PlatformExtractionError: status.HTTP_400_BAD_REQUEST
}
