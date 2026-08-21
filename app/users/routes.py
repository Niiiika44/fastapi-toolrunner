import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_admin, get_current_user
from app.auth.exceptions import NotEnoughPermissionsError
from app.core.openapi import error
from app.users.dependencies import get_user_service
from app.users.models import User
from app.users.schemas import ChangeEmail, ChangePassword, UserResponse, UserUpdate
from app.users.services import UserService

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={401: error("Missing, expired or invalid token")},
)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current user"
)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List all users",
    description="Superusers only.",
    responses={
        403: error("Superuser privileges required"),
    },
)
async def get_all(
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_admin)
) -> list[UserResponse]:
    users = await user_service.show_all()
    return [UserResponse.model_validate(user) for user in users]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user by id",
    responses={
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def get_user_by_id(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_user)
) -> UserResponse:
    user = await user_service.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user profile",
    description=(
        "Updates the given fields only. "
        "Allowed for the account owner and for superusers."
    ),
    responses={
        403: error("Only the account owner or a superuser may update the profile"),
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def update_user(
    user_id: uuid.UUID,
    new_data: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    if current_user.id != user_id and not current_user.is_superuser:
        raise NotEnoughPermissionsError()
    updated_user = await user_service.update(user_id, new_data)
    return UserResponse.model_validate(updated_user)


@router.post(
    "/{user_id}/change-password",
    response_model=UserResponse,
    summary="Change the account password",
    description="Allowed for the account owner only, superusers included.",
    responses={
        400: error("Old password is incorrect"),
        403: error("Only the account owner may change the password"),
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def change_user_password(
    user_id: uuid.UUID,
    user_data: ChangePassword,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    if current_user.id != user_id:
        raise NotEnoughPermissionsError()
    user = await user_service.change_password(
        user_id=user_id,
        old_password=user_data.old_password,
        new_password=user_data.new_password
    )
    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/change-email",
    response_model=UserResponse,
    summary="Change the account email",
    description=(
        "Allowed for the account owner only, superusers included. "
        "Requires the current password. Only `@ispras.ru` addresses are accepted; "
        "the username is re-derived from the new address. "
        "Submitting the current email is a no-op and succeeds."
    ),
    responses={
        400: error("Password is incorrect, or the email domain is not allowed"),
        403: error("Only the account owner may change the email"),
        404: error("User not found"),
        409: error("Another user already uses this email"),
        422: error("Request validation failed"),
    },
)
async def change_user_email(
    user_id: uuid.UUID,
    user_data: ChangeEmail,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    if current_user.id != user_id:
        raise NotEnoughPermissionsError()
    user = await user_service.change_email(
        user_id=user_id,
        new_email=user_data.new_email,
        password=user_data.password
    )
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    description="Allowed for the account owner and for superusers.",
    responses={
        403: error("Only the account owner or a superuser may delete the account"),
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def delete_user(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> None:
    if current_user.id != user_id and not current_user.is_superuser:
        raise NotEnoughPermissionsError()
    await user_service.delete(user_id)
