import asyncio
import logging
import time

from app.core.celery_app import celery_app
from app.core.events import build_event_bus
from app.core.unit_of_work import build_uow
from app.memory_allocator.checker import get_checker
from app.memory_allocator.enums import ValidationStatus
from app.memory_allocator.notifications import StatusNotifier
from app.memory_allocator.services import ValidationService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="memory_allocator.process_validation",
    max_retries=3,
    acks_late=True
)
def process_validation(self, validation_id: int) -> None:
    started_at = time.monotonic()
    logger.info("task.started", extra={
        "task": "process_validation",
        "validation_id": validation_id,
        "retry": self.request.retries,
    })
    try:
        asyncio.run(_process_validation(validation_id))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed(validation_id))
            logger.error("Test validating with id %s failed after %s retries",
                         validation_id, self.max_retries)
            return
        raise self.retry(exc=exc, countdown=min(2 ** self.request.retries, 60)) from exc
    else:
        logger.info("task.finished", extra={
            "task": "process_validation",
            "validation_id": validation_id,
            "duration_ms": round((time.monotonic() - started_at) * 1000),
        })


async def _process_validation(validation_id: int) -> None:
    async with build_uow() as uow, build_event_bus() as bus:
        notifier = StatusNotifier(bus)
        service = ValidationService(uow, get_checker(), notifier=notifier)
        await service.perform_validation(validation_id)


async def _mark_failed(validation_id: int) -> None:
    async with build_uow() as uow, build_event_bus() as bus:
        notifier = StatusNotifier(bus)
        vr = await uow.validations.find_by_id(validation_id)
        if vr is None:
            return
        vr.status = ValidationStatus.FAILED
        await uow.commit()
        await notifier.validation_status_changed(vr)
