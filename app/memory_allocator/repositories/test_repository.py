import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.memory_allocator.models import Tag, TestCase
from app.memory_allocator.schemas import TestFilter, TestPagination


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

    async def find_for_processing(self, test_id: int) -> TestCase | None:
        query = (
            select(TestCase)
            .where(
                TestCase.id == test_id
            )
            .options(
                selectinload(TestCase.platform),
                selectinload(TestCase.uploaded_by),
                selectinload(TestCase.modules),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def find_with_tags(self, test_id: int) -> TestCase | None:
        query = (
            select(TestCase)
            .where(
                TestCase.id == test_id
            )
            .options(
                selectinload(TestCase.tags),
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

    async def list_filtered(
        self,
        filters: TestFilter,
        pagination: TestPagination,
        user_id: uuid.UUID
    ) -> tuple[Sequence[TestCase], int]:
        conditions = []
        if filters.statuses:
            conditions.append(TestCase.status.in_(filters.statuses))
        if filters.name:
            conditions.append(TestCase.name.ilike(f"%{filters.name}%"))
        if filters.platform_ids:
            conditions.append(TestCase.platform_id.in_(filters.platform_ids))
        if filters.tags:
            conditions.append(TestCase.tags.any(Tag.name.in_(filters.tags)))
        if filters.mine:
            conditions.append(TestCase.uploaded_by_id == user_id)

        query_base = select(TestCase).where(*conditions)
        total = await self.session.scalar(
            select(func.count())
            .select_from(TestCase)
            .where(*conditions)
        )
        result_query = (
            query_base
            .options(
                selectinload(TestCase.platform),
                selectinload(TestCase.uploaded_by))
            .order_by(TestCase.id.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        result = (await self.session.execute(result_query)).scalars().all()

        return result, total
