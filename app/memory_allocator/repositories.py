from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory_allocator.models import Platform, TestCase


class PlatformRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_mmu_family(self, mmu_family: str) -> Platform | None:
        query = select(Platform).where(Platform.mmu_family == mmu_family)
        result = await self.session.execute(query)
        platform = result.scalar_one_or_none()
        return platform

    def add(self, platform: Platform) -> None:
        self.session.add(platform)

    async def delete(self, platform: Platform) -> None:
        await self.session.delete(platform)

    async def get_or_create(self, mmu_family: str, page_size: int, config: dict) -> Platform:
        existed_platform = await self.find_by_mmu_family(mmu_family)
        if existed_platform:
            return existed_platform
        platform = Platform(mmu_family=mmu_family, page_size=page_size, config=config)
        self.add(platform)
        await self.session.flush()
        return platform

    async def list_all(self) -> Sequence[Platform]:
        query = select(Platform)
        result = await self.session.execute(query)
        return result.scalars().all()


class TestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, test_id: int) -> TestCase | None:
        test = await self.session.get(TestCase, test_id)
        return test

    def add(self, test: TestCase) -> None:
        self.session.add(test)

    async def delete(self, test: TestCase) -> None:
        await self.session.delete(test)

    async def list_all(self) -> Sequence[TestCase]:
        query = select(TestCase)
        result = await self.session.execute(query)
        return result.scalars().all()
