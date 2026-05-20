from fastapi import Depends

from app.core.unit_of_work import UnitOfWork
from app.users.services import UserService
from app.core.dependencies import get_uow


def get_user_service(uow: UnitOfWork = Depends(get_uow)) -> UserService:
    return UserService(uow)
