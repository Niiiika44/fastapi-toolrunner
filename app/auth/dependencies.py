import uuid
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.auth.services import AuthService
from app.users.services import UserService
from app.auth.exceptions import InvalidTokenError, NotEnoughPermissionsError
from app.users.models import User
from app.core.config import settings
from app.users.dependencies import get_user_service
from app.auth.access_token_encoder import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_auth_service(user_service: UserService = Depends(get_user_service)) -> AuthService:
    return AuthService(user_service)


async def get_current_user(
        user_service: UserService = Depends(get_user_service),
        token: str = Depends(oauth2_scheme),
) -> User:
    try:
        payload = decode_access_token(token, settings.SECRET_KEY, settings.JWT_ALGORITHM)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise InvalidTokenError() from exc
    return await user_service.get_by_id(user_id)


def get_current_admin(
        current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_superuser:
        raise NotEnoughPermissionsError()
    return current_user
