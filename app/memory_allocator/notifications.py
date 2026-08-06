import logging

from app.core.events import EventBus
from app.memory_allocator.models import TestCase, ValidationResult
from app.memory_allocator.schemas import TestStatusEvent, ValidationStatusEvent

logger = logging.getLogger(__name__)


def get_channel_name(test_id: int) -> str:
    return f"test:{test_id}"


class StatusNotifier:
    def __init__(self, bus: EventBus):
        self.bus = bus

    async def validation_status_changed(self, vr: ValidationResult) -> None:
        channel_name = get_channel_name(vr.test_id)
        try:
            validation_status_event = ValidationStatusEvent(
                test_id=vr.test_id,
                validation_id=vr.id,
                status=vr.status,
                valid=vr.valid
            ).model_dump_json()
            await self.bus.publish(channel_name, validation_status_event)
            logger.debug("event.published", extra={
                "channel": channel_name,
                "event": "validation.status",
                "status": str(vr.status)
            })
        except Exception as exc:
            logger.warning("event.publish_failed", extra={
                "error": str(exc),
                "channel": channel_name,
                "event": "validation.status",
                "status": str(vr.status)
            })

    async def test_status_changed(self, test: TestCase) -> None:
        channel_name = get_channel_name(test.id)
        try:
            test_status_event = TestStatusEvent(
                test_id=test.id,
                status=test.status,
                error_message=test.error_message
            ).model_dump_json()
            await self.bus.publish(channel_name, test_status_event)
            logger.debug("event.published", extra={
                "channel": channel_name,
                "event": "test.status",
                "status": str(test.status)
            })
        except Exception as exc:
            logger.warning("event.publish_failed", extra={
                "error": str(exc),
                "channel": channel_name,
                "event": "test.status",
                "status": str(test.status)
            })
