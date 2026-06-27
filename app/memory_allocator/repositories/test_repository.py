from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.memory_allocator.models import TestCase


class TestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, test_id: int) -> TestCase | None:
        query = (
            select(TestCase)
            .where(
                TestCase.id == test_id
            )
            .options(
                selectinload(TestCase.platform),
                selectinload(TestCase.uploaded_by),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def add(self, test: TestCase) -> None:
        self.session.add(test)

    async def delete(self, test: TestCase) -> None:
        await self.session.delete(test)

    async def list_all(self) -> Sequence[TestCase]:
        query = (
            select(TestCase)
            .options(
                selectinload(TestCase.platform),
                selectinload(TestCase.uploaded_by),
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()
