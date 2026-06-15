import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_admin, get_current_user
from app.auth.exceptions import NotEnoughPermissionsError
from app.users.dependencies import get_user_service
from app.users.models import User
from app.users.schemas import ChangeEmail, ChangePassword, UserResponse, UserUpdate
from app.users.services import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me",
            response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return current_user


@router.get("",
            response_model=list[UserResponse])
async def get_all(
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_admin)
) -> list[UserResponse]:
    users = await user_service.show_all()
    return list(users)


@router.get("/{user_id}",
            response_model=UserResponse)
async def get_user_by_id(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_user)
) -> UserResponse:
    user = await user_service.get_by_id(user_id)
    return user


@router.patch("/{user_id}",
              response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    new_data: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    if current_user.id != user_id and not current_user.is_superuser:
        raise NotEnoughPermissionsError()
    updated_user = await user_service.update(user_id, new_data)
    return updated_user


@router.post("/{user_id}/change-password",
             response_model=UserResponse)
async def change_user_password(
    user_id: uuid.UUID,
    user_data: ChangePassword,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    if current_user.id != user_id:
        raise NotEnoughPermissionsError()
    return await user_service.change_password(
        user_id=user_id,
        old_password=user_data.old_password,
        new_password=user_data.new_password
    )


@router.post("/{user_id}/change-email",
             response_model=UserResponse)
async def change_user_email(
    user_id: uuid.UUID,
    user_data: ChangeEmail,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    if current_user.id != user_id:
        raise NotEnoughPermissionsError()
    return await user_service.change_email(
        user_id=user_id,
        new_email=user_data.new_email,
        password=user_data.password
    )


@router.delete("/{user_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> None:
    if current_user.id != user_id and not current_user.is_superuser:
        raise NotEnoughPermissionsError()
    await user_service.delete(user_id)
