from fastapi import status

from app.core.exceptions import DomainError
from app.users.exceptions import (
    UserNotFoundError, EmailDomainNotAllowedError,
    UserAlreadyExistsError, InvalidPasswordError
)
from app.auth.exceptions import (
    InvalidCredentialsError, InvalidTokenError, NotEnoughPermissionsError
)


EXCEPTION_STATUS_MAP: dict[type[DomainError], int] = {
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
    EmailDomainNotAllowedError: status.HTTP_400_BAD_REQUEST,
    UserAlreadyExistsError: status.HTTP_409_CONFLICT,
    InvalidPasswordError: status.HTTP_400_BAD_REQUEST,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidTokenError: status.HTTP_401_UNAUTHORIZED,
    NotEnoughPermissionsError: status.HTTP_403_FORBIDDEN
}
