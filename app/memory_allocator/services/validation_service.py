import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.checker import Checker
from app.memory_allocator.enums import TestStatus, ValidationStatus
from app.memory_allocator.exceptions import TestNotFoundError, TestNotValidatableError
from app.memory_allocator.models import ValidationResult
from app.memory_allocator.schemas import ValidationDomain

logger = logging.getLogger(__name__)


class ValidationService:
    def __init__(self, uow: UnitOfWork,
                 checker: Checker,
                 enqueue_validation: Callable[[int], object] | None = None):
        self.uow = uow
        self.checker = checker
        self.enqueue_validation = enqueue_validation

    async def request_validation(self, test_id: int) -> ValidationDomain:
        test = await self.uow.tests.find_by_id(test_id)
        if test is None:
            raise TestNotFoundError(test_id)
        if test.status != TestStatus.PARSED:
            raise TestNotValidatableError(test_id, test.status)

        vr = ValidationResult(test=test, status=ValidationStatus.PENDING)
        self.uow.validations.add(vr)
        await self.uow.commit()

        if self.enqueue_validation is None:
            raise RuntimeError("enqueue_validation is not configurated")
        self.enqueue_validation(vr.id)

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

        outcome = await self.checker.check(vr.test)
        vr.valid = outcome.valid
        vr.status = ValidationStatus.COMPLETED
        vr.schema_valid = outcome.schema_valid
        vr.errors = outcome.errors
        vr.checker_version = self.checker.version
        vr.checked_at = datetime.now(UTC)

        await self.uow.commit()

    async def list_for_test(self, test_id: int) -> list[ValidationDomain]:
        if await self.uow.tests.find_by_id(test_id) is None:
            raise TestNotFoundError(test_id)
        validations = await self.uow.validations.list_by_test(test_id)
        return [ValidationDomain.model_validate(t) for t in validations]
