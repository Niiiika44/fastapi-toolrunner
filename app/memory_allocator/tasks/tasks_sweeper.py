import asyncio
import logging
import time
from datetime import timedelta

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.unit_of_work import build_uow
from app.memory_allocator.services.sweeper_service import SweeperService
from app.memory_allocator.tasks.tasks_testcase import process_test
from app.memory_allocator.tasks.tasks_validation import process_validation

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    name="memory_allocator.sweep_stale_jobs",
    max_retries=0
)
def sweep_stale_jobs() -> dict[str, int]:
    started_at = time.monotonic()
    logger.debug("task.started", extra={"task": "sweep_stale_jobs"})
    requeued = asyncio.run(_sweep())
    logger.log(logging.INFO if any(requeued.values()) else logging.DEBUG,
               "task.finished", extra={
                   "task": "sweep_stale_jobs",
                   "duration_ms": round((time.monotonic() - started_at) * 1000),
                   "requeued": requeued})
    return requeued


async def _sweep() -> dict[str, int]:
    async with build_uow() as uow:
        service = SweeperService(uow, process_test.delay, process_validation.delay)
        stale_after = timedelta(seconds=settings.SWEEPER_STALE_AFTER_SECONDS)
        tests = await service.requeue_stale_pending(
            stale_after=stale_after,
            limit=settings.SWEEPER_BATCH_LIMIT
        )
        validations = await service.requeue_stale_validations(
            stale_after=stale_after,
            limit=settings.SWEEPER_BATCH_LIMIT
        )
        return {"tests": tests, "validations": validations}
