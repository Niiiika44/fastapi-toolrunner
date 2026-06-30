import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.dependencies import get_storage
from app.core.exceptions import DomainError
from app.core.unit_of_work import build_uow
from app.memory_allocator.enums import TestStatus
from app.memory_allocator.services import IngestionService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="memory_allocator.process_test",
    max_retries=3,
    acks_late=True
)
def process_test(self, test_id: int) -> None:
    try:
        asyncio.run(_process_test(test_id))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_error(test_id, "Internal processing error after retries"))
            logger.error("Test %s failed after %s retries", test_id, self.max_retries)
            return
        raise self.retry(exc=exc, countdown=min(2 ** self.request.retries, 60)) from exc


async def _process_test(test_id: int) -> None:
    async with build_uow() as uow:
        test = await uow.tests.find_for_processing(test_id)
        if test is None:
            logger.error("Test %s not found, skipping processing", test_id)
            return
        if test.status == TestStatus.PARSED:
            logger.info("Test %s already parsed — skip (redelivery)", test_id)
            return

        test.status = TestStatus.PROCESSING
        await uow.commit()

        storage_key = f"uploads/{test_id}.zip"
        storage = get_storage()
        try:
            content = await storage.load(storage_key)

            service = IngestionService(uow, storage)
            await service.process_upload(test, content)
        except DomainError as exc:
            await uow.rollback()
            test.status = TestStatus.ERROR
            test.error_message = str(exc)
            await uow.commit()
            logger.warning("Test %s failed parsing: %s", test_id, exc)
        except Exception:
            await uow.rollback()
            raise
        else:
            await _safe_delete(storage, storage_key)


async def _mark_error(test_id: int, message: str) -> None:
    async with build_uow() as uow:
        test = await uow.tests.find_by_id(test_id)
        if test is None:
            return
        test.status = TestStatus.ERROR
        test.error_message = message
        await uow.commit()


async def _safe_delete(storage, key: str) -> None:
    try:
        await storage.delete(key)
    except KeyError:
        pass
    except Exception as exc:
        logger.warning("Failed to delete %s: %s", key, exc)
