import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        user = await self.session.get(User, user_id)
        return user

    async def find_by_username(self, username: str) -> User | None:
        query = select(User).where(User.username == username)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        return user

    async def find_by_email(self, email: str) -> User | None:
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        return user

    def add(self, user: User) -> None:
        self.session.add(user)

    async def delete(self, user: User) -> None:
        await self.session.delete(user)

    async def list_all(self) -> Sequence[User]:
        query = select(User)
        result = await self.session.execute(query)
        return result.scalars().all()
