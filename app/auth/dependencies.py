import logging
import uuid
from collections.abc import Iterable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.auth.access_token_encoder import decode_access_token
from app.auth.enums import Permission
from app.auth.exceptions import InvalidTokenError, NotEnoughPermissionsError
from app.auth.permissions import KNOWN_PERMISSIONS, resolve_permissions
from app.auth.services import AuthService
from app.core.config import get_settings
from app.users.dependencies import get_user_service
from app.users.exceptions import UserNotFoundError
from app.users.models import User
from app.users.services import UserService

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

settings = get_settings()


def get_auth_service(user_service: UserService = Depends(get_user_service)) -> AuthService:
    return AuthService(user_service)


async def authenticate_user(token: str, user_service: UserService) -> User:
    try:
        payload = decode_access_token(
            token,
            settings.SECRET_KEY.get_secret_value(),
            settings.JWT_ALGORITHM
        )
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise InvalidTokenError() from exc
    user = await user_service.find_by_id(user_id)
    if user is None:
        raise UserNotFoundError(id=user_id)
    return user


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        user_service: UserService = Depends(get_user_service),
) -> User:
    return await authenticate_user(token, user_service)


def get_current_admin(
        current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_superuser:
        raise NotEnoughPermissionsError()
    return current_user


def has_permissions(user: User, required: Iterable[Permission]) -> bool:
    if user.is_superuser:
        return True
    granted = [grant.permission for grant in user.permissions]
    for name in granted:
        if name not in KNOWN_PERMISSIONS:
            logger.warning("user.unknown_permission", extra={
                "user_id": str(user.id),
                "permission": name,
            })
    return resolve_permissions(user.job_title, granted).issuperset(required)
