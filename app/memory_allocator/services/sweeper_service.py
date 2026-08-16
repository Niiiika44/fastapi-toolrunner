import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.core.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class SweeperService:
    def __init__(self, uow: UnitOfWork,
                 enqueue_processing: Callable[[int], object]):
        self.uow = uow
        self.enqueue_processing = enqueue_processing

    async def requeue_stale_pending(self, stale_after: timedelta, limit: int) -> int:
        cutoff = datetime.now(UTC) - stale_after
        logger.debug("sweeper.scan", extra={"cutoff": cutoff, "limit": limit})
        tests = await self.uow.tests.find_stale_pending(older_than=cutoff, limit=limit)

        requeued: list[int] = []
        failed: list[int] = []
        for test in tests:
            try:
                self.enqueue_processing(test.id)
            except Exception as exc:
                failed.append(test.id)
                logger.warning("sweeper.enqueue_failed",
                               extra={"test_id": test.id, "error": repr(exc)})
            else:
                requeued.append(test.id)

        if failed and not requeued:
            raise RuntimeError(
                f"sweeper failed to enqueue all {len(failed)} stale tests"
            )
        if requeued:
            logger.info("sweeper.requeued",
                        extra={"count": len(requeued), "test_ids": requeued,
                               "failed": len(failed)})
        return len(requeued)
