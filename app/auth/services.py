from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.auth.schemas import UserLogin, TokenResponse
from app.auth.hash_utils import verify_password
from app.auth.acess_token_encoder import create_acess_token
from app.core.config import settings
from app.users.services import find_user_by_email


async def authenticate_user(user_data: UserLogin, db: AsyncSession):
    user = await find_user_by_email(user_data.email, db=db)
    if not (user and verify_password(user_data.password, user.password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid email or password")
    data_to_encode = {"sub": str(user.id)}
    access_token = create_acess_token(
        data_to_encode,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        settings.SECRET_KEY,
        settings.JWT_ALGORITHM
    )
    return TokenResponse(access_token=access_token, token_type="bearer")
