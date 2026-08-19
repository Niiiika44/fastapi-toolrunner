import logging

from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.enums import TestStatus, ValidationStatus
from app.memory_allocator.models import DeadLetter, TestCase, ValidationResult
from app.memory_allocator.notifications import StatusNotifier
from app.memory_allocator.schemas import DeadLetterMessage

logger = logging.getLogger(__name__)

PROCESS_TEST_TASK = "memory_allocator.process_test"
PROCESS_VALIDATION_TASK = "memory_allocator.process_validation"

UNFINISHED_TEST_STATUSES = (TestStatus.PENDING, TestStatus.PROCESSING)
UNFINISHED_VALIDATION_STATUSES = (ValidationStatus.PENDING, ValidationStatus.RUNNING)


class DeadLetterService:
    def __init__(self, uow: UnitOfWork, notifier: StatusNotifier | None = None):
        self.uow = uow
        self.notifier = notifier

    async def record(self, message: DeadLetterMessage) -> int:
        letter = DeadLetter(
            task_name=message.task_name,
            task_id=message.task_id,
            args=message.args,
            request_id=message.request_id,
            reason=message.reason,
            delivered_count=message.delivered_count,
        )
        self.uow.dead_letters.add(letter)

        entity = await self._terminate_owner(message)
        await self.uow.commit()

        logger.error("dlq.recorded", extra={
            "task_name": message.task_name,
            "task_id": message.task_id,
            "reason": message.reason,
            "delivered_count": message.delivered_count,
            "terminated": entity is not None,
        })
        if entity is not None and self.notifier is not None:
            await self._notify(entity)

        return letter.id

    async def _terminate_owner(
        self,
        message: DeadLetterMessage
    ) -> TestCase | ValidationResult | None:
        owner_id = self._owner_id(message)
        if owner_id is None:
            return None

        reason = self._failure_reason(message)
        if message.task_name == PROCESS_TEST_TASK:
            test = await self.uow.tests.find_by_id(owner_id)
            if test is None or test.status not in UNFINISHED_TEST_STATUSES:
                return None
            test.status = TestStatus.ERROR
            test.error_message = reason
            return test

        validation = await self.uow.validations.find_by_id(owner_id)
        if validation is None or validation.status not in UNFINISHED_VALIDATION_STATUSES:
            return None
        validation.status = ValidationStatus.FAILED
        return validation

    def _owner_id(self, message: DeadLetterMessage) -> int | None:
        if message.task_name not in (PROCESS_TEST_TASK, PROCESS_VALIDATION_TASK):
            return None
        if not message.args:
            logger.warning("dlq.owner_unknown", extra={
                "task_name": message.task_name,
                "task_id": message.task_id,
            })
            return None
        owner_id = message.args[0]
        if not isinstance(owner_id, int):
            logger.warning("dlq.owner_unknown", extra={
                "task_name": message.task_name,
                "task_id": message.task_id,
                "task_args": message.args,
            })
            return None
        return owner_id

    def _failure_reason(self, message: DeadLetterMessage) -> str:
        return f"Task moved to the dead-letter queue (reason: {message.reason or "unknown"})"

    async def _notify(self, entity: TestCase | ValidationResult) -> None:
        if isinstance(entity, TestCase):
            await self.notifier.test_status_changed(entity)
        else:
            await self.notifier.validation_status_changed(entity)
