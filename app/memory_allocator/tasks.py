import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.dependencies import get_storage
from app.core.exceptions import DomainError
from app.core.unit_of_work import build_uow
from app.memory_allocator.enums import TestStatus
from app.memory_allocator.services import IngestionService

logger = logging.getLogger(__name__)


@celery_app.task(name="memory_allocator.process_test")
def process_test(test_id: int) -> None:
    asyncio.run(_process_test(test_id))


async def _process_test(test_id: int) -> None:
    async with build_uow() as uow:
        test = await uow.tests.find_by_id(test_id)
        if test is None:
            logger.error("Test %s not found, skipping processing", test_id)
            return

        test.status = TestStatus.PROCESSING
        await uow.commit()

        storage = get_storage()
        content = await storage.load(f"uploads/{test_id}.zip")

        service = IngestionService(uow, storage)
        try:
            await service.process_upload(test, content)
        except DomainError as exc:
            await uow.rollback()
            test.status = TestStatus.ERROR
            test.error_message = str(exc)
            await uow.commit()
            logger.warning("Test %s failed parsing: %s", test_id, exc)
