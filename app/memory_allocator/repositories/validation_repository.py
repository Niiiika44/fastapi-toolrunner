from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.memory_allocator.models import ValidationResult


class ValidationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, validation: ValidationResult) -> None:
        self.session.add(validation)

    async def find_by_id(self, validation_id: int) -> ValidationResult | None:
        query = (
            select(ValidationResult)
            .where(ValidationResult.id == validation_id)
            .options(selectinload(ValidationResult.test))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_test(self, test_id: int) -> Sequence[ValidationResult]:
        query = (
            select(ValidationResult)
            .where(ValidationResult.test_id == test_id)
            .order_by(ValidationResult.id.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()
