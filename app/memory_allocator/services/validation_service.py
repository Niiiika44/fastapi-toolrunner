import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.checker import Checker
from app.memory_allocator.enums import TestStatus, ValidationStatus
from app.memory_allocator.exceptions import TestNotFoundError, TestNotValidatableError
from app.memory_allocator.models import ValidationResult
from app.memory_allocator.notifications import StatusNotifier
from app.memory_allocator.schemas import ValidationDomain

logger = logging.getLogger(__name__)


class ValidationService:
    def __init__(self, uow: UnitOfWork,
                 checker: Checker,
                 enqueue_validation: Callable[[int], object] | None = None,
                 notifier: StatusNotifier | None = None):
        self.uow = uow
        self.checker = checker
        self.enqueue_validation = enqueue_validation
        self.notifier = notifier

    async def request_validation(self, test_id: int) -> ValidationDomain:
        test = await self.uow.tests.find_by_id(test_id)
        if test is None:
            raise TestNotFoundError(test_id)
        if test.status != TestStatus.PARSED:
            logger.info("validation.rejected", extra={
                "test_id": test_id,
                "status": test.status,
            })
            raise TestNotValidatableError(test_id, test.status)

        vr = ValidationResult(test=test, status=ValidationStatus.PENDING)
        self.uow.validations.add(vr)
        await self.uow.commit()

        if self.enqueue_validation is None:
            raise RuntimeError("enqueue_validation is not configurated")
        self.enqueue_validation(vr.id)
        logger.info("validation.requested", extra={
            "test_id": test_id,
            "validation_id": vr.id,
        })
        if self.notifier is not None:
            await self.notifier.validation_status_changed(vr)

        return ValidationDomain.model_validate(vr)

    async def perform_validation(self, validation_id: int) -> None:
        vr = await self.uow.validations.find_by_id(validation_id)
        if vr is None:
            logger.error("Validation id %s not found, skipping", validation_id)
            return
        if vr.status == ValidationStatus.COMPLETED:
            return
        vr.status = ValidationStatus.RUNNING
        await self.uow.commit()
        if self.notifier is not None:
            await self.notifier.validation_status_changed(vr)

        outcome = await self.checker.check(vr.test)
        vr.valid = outcome.valid
        vr.status = ValidationStatus.COMPLETED
        vr.schema_valid = outcome.schema_valid
        vr.errors = outcome.errors
        vr.checker_version = self.checker.version
        vr.checked_at = datetime.now(UTC)

        await self.uow.commit()
        logger.info("validation.completed", extra={
            "validation_id": vr.id,
            "test_id": vr.test_id,
            "valid": vr.valid,
            "schema_valid": vr.schema_valid,
            "checker_version": vr.checker_version,
        })
        if self.notifier is not None:
            await self.notifier.validation_status_changed(vr)

    async def list_for_test(self, test_id: int) -> list[ValidationDomain]:
        if await self.uow.tests.find_by_id(test_id) is None:
            raise TestNotFoundError(test_id)
        validations = await self.uow.validations.list_by_test(test_id)
        return [ValidationDomain.model_validate(t) for t in validations]
