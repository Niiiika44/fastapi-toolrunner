from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.events import EventBus, current_event_bus
from app.core.storage import LocalStorage, S3Storage, StorageBackend
from app.core.unit_of_work import UnitOfWork
from app.db.database import get_db

settings = get_settings()


def get_uow(session: AsyncSession = Depends(get_db)) -> UnitOfWork:
    return UnitOfWork(session)


def get_storage() -> StorageBackend:
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage(
            bucket=settings.S3_BUCKET,
            access_key=settings.S3_ACCESS_KEY.get_secret_value(),
            secret_key=settings.S3_SECRET_KEY.get_secret_value(),
            region=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
            public_endpoint_url=settings.S3_PUBLIC_ENDPOINT_URL,
        )
    return LocalStorage(Path(settings.STORAGE_PATH))


def get_event_bus() -> EventBus:
    return current_event_bus()
