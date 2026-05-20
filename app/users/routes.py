# POST /users/{user_id}/change-password	смена пароля
# POST /users/{user_id}/change-email	смена email
# DELETE /users/{user_id}
import uuid
from fastapi import APIRouter, Depends

from app.auth.exceptions import NotEnoughPermissionsError
from app.users.schemas import UserResponse, UserUpdate
from app.users.models import User
from app.users.dependencies import get_user_service
from app.users.services import UserService
from app.auth.dependencies import get_current_user, get_current_admin


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me",
            response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return current_user


@router.get("/",
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
    user_service: UserService = Depends(get_user_service)
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
