from fastapi import Depends

from app.core.dependencies import get_event_bus, get_storage, get_uow
from app.core.events import EventBus
from app.core.storage import StorageBackend
from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.checker import Checker, get_checker
from app.memory_allocator.notifications import StatusNotifier
from app.memory_allocator.services import (
    IngestionService,
    PlatformService,
    TagService,
    TestcaseService,
    ValidationService,
)
from app.memory_allocator.services.export_service import ExportService
from app.memory_allocator.tasks.tasks_testcase import process_test
from app.memory_allocator.tasks.tasks_validation import process_validation


def get_ingestion_service(
    uow: UnitOfWork = Depends(get_uow),
    storage: StorageBackend = Depends(get_storage)
) -> IngestionService:
    return IngestionService(uow=uow, storage=storage, enqueue_processing=process_test.delay)


def get_test_service(uow: UnitOfWork = Depends(get_uow)) -> TestcaseService:
    return TestcaseService(uow=uow)


def get_validation_service(
    uow: UnitOfWork = Depends(get_uow),
    checker: Checker = Depends(get_checker)
) -> ValidationService:
    return ValidationService(uow=uow, checker=checker, enqueue_validation=process_validation.delay)


def get_platform_service(uow: UnitOfWork = Depends(get_uow)) -> PlatformService:
    return PlatformService(uow=uow)


def get_tag_service(uow: UnitOfWork = Depends(get_uow)) -> TagService:
    return TagService(uow=uow)


def get_export_service(
    uow: UnitOfWork = Depends(get_uow),
    storage: StorageBackend = Depends(get_storage)
) -> ExportService:
    return ExportService(uow=uow, storage=storage)


def get_status_notifier(bus: EventBus = Depends(get_event_bus)) -> StatusNotifier:
    return StatusNotifier(bus=bus)
