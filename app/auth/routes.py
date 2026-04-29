from fastapi import APIRouter
from app.users.schemas import UserCreate


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/")
async def register_user(user_data: UserCreate):
    