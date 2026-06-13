from sqlalchemy.ext.asyncio import AsyncSession

from app.memory_allocator.repositories import PlatformRepository, TestRepository
from app.users.repositories import UserRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.tests = TestRepository(session)
        self.platforms = PlatformRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def refresh(self, obj) -> None:
        await self.session.refresh(obj)

    async def flush(self) -> None:
        await self.session.flush()
