from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.memory_allocator.models import Tag


class TagRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, tag: Tag) -> None:
        self.session.add(tag)

    async def find_by_id(self, tag_id: int) -> Tag | None:
        query = (
            select(Tag)
            .where(Tag.id == tag_id)
            .options(selectinload(Tag.tests))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def find_by_name(self, tag_name: str) -> Tag | None:
        query = (
            select(Tag)
            .where(Tag.name == tag_name)
            .options(selectinload(Tag.tests))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[Tag]:
        query = (
            select(Tag)
            .options(selectinload(Tag.tests))
            .order_by(Tag.id.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete(self, tag: Tag) -> None:
        await self.session.delete(tag)
