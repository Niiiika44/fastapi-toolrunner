from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory_allocator.models import DeadLetter
from app.memory_allocator.schemas import DeadLetterPagination


class DeadLetterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, letter: DeadLetter) -> None:
        self.session.add(letter)

    async def list_all(self, pagination: DeadLetterPagination) -> Sequence[DeadLetter]:
        query = (
            select(DeadLetter)
            .order_by(DeadLetter.id.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        return (await self.session.execute(query)).scalars().all()
