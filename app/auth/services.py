from app.auth.schemas import TokenResponse
from app.auth.exceptions import InvalidCredentialsError
from app.auth.hash_utils import verify_password
from app.auth.access_token_encoder import create_access_token
from app.core.config import settings
from app.users.services import UserService


class AuthService:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    async def authenticate_user(self, email: str, password: str) -> TokenResponse:
        user = await self.user_service.find_by_email(email)
        if not (user and verify_password(password, user.password)):
            raise InvalidCredentialsError()
        data_to_encode = {"sub": str(user.id)}
        access_token = create_access_token(
            data_to_encode,
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            settings.SECRET_KEY,
            settings.JWT_ALGORITHM
        )
        return TokenResponse(access_token=access_token, token_type="bearer")
