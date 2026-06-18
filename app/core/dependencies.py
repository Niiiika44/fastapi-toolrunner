from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.storage import LocalStorage, StorageBackend
from app.core.unit_of_work import UnitOfWork
from app.db.database import get_db

settings = get_settings()


def get_uow(session: AsyncSession = Depends(get_db)) -> UnitOfWork:
    return UnitOfWork(session)


def get_storage() -> StorageBackend:
    return LocalStorage(Path(settings.STORAGE_PATH))
