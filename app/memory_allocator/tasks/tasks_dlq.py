import asyncio
import logging
import time

from kombu.serialization import loads

from app.core.celery_app import DEAD_LETTER_QUEUE, celery_app
from app.core.config import get_settings
from app.core.events import build_event_bus
from app.core.unit_of_work import build_uow
from app.memory_allocator.notifications import StatusNotifier
from app.memory_allocator.schemas import DeadLetterMessage
from app.memory_allocator.services.deadletter_service import DeadLetterService

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="memory_allocator.drain_dlq", max_retries=0)
def drain_dlq() -> int:
    started_at = time.monotonic()
    logger.debug("task.started", extra={"task": "drain_dlq"})
    drained = asyncio.run(_drain())
    logger.log(logging.INFO if drained > 0 else logging.DEBUG,
               "task.finished", extra={
                   "task": "drain_dlq",
                   "duration_ms": round((time.monotonic() - started_at) * 1000),
                   "drained": drained})
    return drained


async def _drain() -> int:
    async with build_uow() as uow, build_event_bus() as bus:
        notifier = StatusNotifier(bus)
        service = DeadLetterService(uow, notifier)
        drained = 0
        with celery_app.connection_for_write() as conn:
            channel = conn.default_channel
            for _ in range(settings.DLQ_BATCH_LIMIT):
                raw = channel.basic_get(DEAD_LETTER_QUEUE, no_ack=False)
                if raw is None:
                    break
                message = _parse_envelope(raw)
                await service.record(message)
                channel.basic_ack(raw.delivery_tag)
                drained += 1
        return drained


def _parse_envelope(raw) -> DeadLetterMessage:
    headers = raw.headers or {}
    decoded = loads(raw.body, raw.content_type, raw.content_encoding)
    args = decoded[0] if isinstance(decoded, list) and decoded else None
    deaths = headers.get("x-death") or [{}]
    msg = DeadLetterMessage(
        task_name=headers.get("task", "unknown"),
        task_id=headers.get("id", "unknown"),
        args=args,
        request_id=headers.get("request_id"),
        reason=headers.get("x-last-death-reason"),
        delivered_count=deaths[0].get("count")
    )
    return msg
