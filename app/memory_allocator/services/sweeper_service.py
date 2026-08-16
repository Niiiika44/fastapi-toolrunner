import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta

from app.core.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class SweeperService:
    def __init__(self, uow: UnitOfWork,
                 enqueue_processing: Callable[[int], object],
                 enqueue_validation: Callable[[int], object]):
        self.uow = uow
        self.enqueue_processing = enqueue_processing
        self.enqueue_validation = enqueue_validation

    def _requeue(self, items: Sequence, dispatch: Callable[[int], object], kind: str) -> int:
        requeued: list[int] = []
        failed: list[int] = []
        for item in items:
            try:
                dispatch(item.id)
            except Exception as exc:
                failed.append(item.id)
                logger.warning("sweeper.enqueue_failed",
                               extra={"kind": kind, "item_id": item.id, "error": repr(exc)})
            else:
                requeued.append(item.id)

        if failed and not requeued:
            raise RuntimeError(f"sweeper failed to enqueue all {len(failed)} stale {kind}")
        if requeued:
            logger.info("sweeper.requeued",
                        extra={"kind": kind, "count": len(requeued),
                               "ids": requeued, "failed": len(failed)})
        return len(requeued)

    async def requeue_stale_pending(self, stale_after: timedelta, limit: int) -> int:
        cutoff = datetime.now(UTC) - stale_after
        logger.debug("sweeper.scan", extra={
            "cutoff": cutoff,
            "limit": limit,
            "kind": "tests"
        })
        tests = await self.uow.tests.find_stale_pending(older_than=cutoff, limit=limit)

        return self._requeue(tests, self.enqueue_processing, "tests")

    async def requeue_stale_validations(self, stale_after: timedelta, limit: int) -> int:
        cutoff = datetime.now(UTC) - stale_after
        logger.debug("sweeper.scan", extra={
            "cutoff": cutoff,
            "limit": limit,
            "kind": "validations"
        })
        validations = await self.uow.validations.find_stale_pending(older_than=cutoff, limit=limit)

        return self._requeue(validations, self.enqueue_validation, "validations")
