from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import get_auth_service
from app.auth.schemas import TokenResponse
from app.auth.services import AuthService
from app.core.openapi import error
from app.users.dependencies import get_user_service
from app.users.schemas import UserCreate, UserResponse
from app.users.services import UserService

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Creates a user account. Only `@ispras.ru` email addresses are accepted. "
        "The username is derived from the local part of the email."
    ),
    responses={
        400: error("Email domain is not allowed"),
        409: error("User with this email already exists"),
        422: error("Request validation failed"),
    },
)
async def register_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
) -> UserResponse:
    new_user = await user_service.create(user_data)
    return UserResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain an access token",
    description=(
        "OAuth2 password flow. Send the credentials as a form body: "
        "`username` holds the **email address**, `password` holds the password. "
        "The returned bearer token authorizes both HTTP endpoints and the "
        "status WebSocket (see README)."
    ),
    responses={
        401: error("Invalid email or password"),
        422: error("Request validation failed"),
    },
)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    return await auth_service.authenticate_user(form_data.username, form_data.password)
