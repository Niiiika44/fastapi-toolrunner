from fastapi import Depends

from app.core.dependencies import get_storage, get_uow
from app.core.storage import StorageBackend
from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.services import IngestionService, TestcaseService


def get_ingestion_service(
        uow: UnitOfWork = Depends(get_uow),
        storage: StorageBackend = Depends(get_storage)
) -> IngestionService:
    return IngestionService(uow=uow, storage=storage)


def get_test_service(uow: UnitOfWork = Depends(get_uow)) -> TestcaseService:
    return TestcaseService(uow=uow)
