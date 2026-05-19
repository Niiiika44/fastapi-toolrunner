from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import UserLogin, TokenResponse
from app.auth.services import authenticate_user
from app.users.schemas import UserResponse, UserCreate
from app.users.services import create_user
from app.db.database import get_db


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register",
             response_model=UserResponse,
             status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    new_user = await create_user(user_data, db=db)
    return new_user


@router.post("/login",
             response_model=TokenResponse)
async def login_user(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    access_token = await authenticate_user(user_data, db=db)
    return access_token
