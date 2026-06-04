from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.schemas import TokenResponse
from app.users.schemas import UserResponse, UserCreate
from app.users.services import UserService
from app.auth.services import AuthService
from app.users.dependencies import get_user_service
from app.auth.dependencies import get_auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register",
             response_model=UserResponse,
             status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
) -> UserResponse:
    new_user = await user_service.create(user_data)
    return new_user


@router.post("/login",
             response_model=TokenResponse)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    access_token = await auth_service.authenticate_user(form_data.username, form_data.password)
    return access_token
