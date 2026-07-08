import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.unit_of_work import build_uow
from app.memory_allocator.checker import get_checker
from app.memory_allocator.enums import ValidationStatus
from app.memory_allocator.services import ValidationService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="memory_allocator.process_validation",
    max_retries=3,
    acks_late=True
)
def process_validation(self, validation_id: int) -> None:
    try:
        asyncio.run(_process_validation(validation_id))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed(validation_id))
            logger.error("Test validating with id %s failed after %s retries",
                         validation_id, self.max_retries)
            return
        raise self.retry(exc=exc, countdown=min(2 ** self.request.retries, 60)) from exc


async def _process_validation(validation_id: int) -> None:
    async with build_uow() as uow:
        service = ValidationService(uow, get_checker())
        await service.perform_validation(validation_id)


async def _mark_failed(validation_id: int) -> None:
    async with build_uow() as uow:
        vr = await uow.validations.find_by_id(validation_id)
        if vr is None:
            return
        vr.status = ValidationStatus.FAILED
        await uow.commit()
