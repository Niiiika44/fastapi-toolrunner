from fastapi import Depends

from app.core.dependencies import get_storage, get_uow
from app.core.storage import StorageBackend
from app.core.unit_of_work import UnitOfWork
from app.users.services import UserService
from app.users.services.avatar_service import AvatarService


def get_user_service(
    uow: UnitOfWork = Depends(get_uow),
    storage: StorageBackend = Depends(get_storage)
) -> UserService:
    return UserService(uow, storage)


def get_avatar_service(
    uow: UnitOfWork = Depends(get_uow),
    storage: StorageBackend = Depends(get_storage)
) -> AvatarService:
    return AvatarService(uow=uow, storage=storage)
