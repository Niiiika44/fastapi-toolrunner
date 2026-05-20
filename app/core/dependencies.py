from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.db.database import get_db


def get_uow(session: AsyncSession = Depends(get_db)) -> UnitOfWork:
    return UnitOfWork(session)
