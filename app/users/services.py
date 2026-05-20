import uuid
from typing import Sequence

from app.core.unit_of_work import UnitOfWork
from app.users.models import User
from app.users.schemas import UserCreate, UserUpdate
from app.users.exceptions import (
    UserNotFoundError,
    EmailDomainNotAllowedError,
    UserAlreadyExistsError,
    InvalidPasswordError
)
from app.auth.hash_utils import get_password_hash, verify_password


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.uow.users.find_by_id(user_id)

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        user = await self.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(id=user_id)
        return user

    async def find_by_username(self, username: str) -> User | None:
        return await self.uow.users.find_by_username(username)

    async def get_by_username(self, username: str) -> User:
        user = await self.find_by_username(username)
        if not user:
            raise UserNotFoundError(username=username)
        return user

    async def find_by_email(self, email: str) -> User | None:
        return await self.uow.users.find_by_email(email)

    async def get_by_email(self, email: str) -> User:
        user = await self.find_by_email(email)
        if not user:
            raise UserNotFoundError(email=email)
        return user

    async def create(self, user_data: UserCreate) -> User:
        if not user_data.email.endswith("@ispras.ru"):
            raise EmailDomainNotAllowedError(email=user_data.email)

        existing_user = await self.uow.users.find_by_email(user_data.email)
        if existing_user:
            raise UserAlreadyExistsError(email=user_data.email)

        username = user_data.email.rsplit("@", maxsplit=1)[0]
        hashed = get_password_hash(user_data.password)
        new_user = User(**user_data.model_dump(exclude={"password"}),
                        username=username, password=hashed)
        self.uow.users.add(new_user)
        await self.uow.commit()
        await self.uow.refresh(new_user)
        return new_user

    async def update(self, user_id: uuid.UUID, user_data: UserUpdate) -> User:
        user = await self.get_by_id(user_id)
        for field, value in user_data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.uow.commit()
        await self.uow.refresh(user)
        return user

    async def change_password(
            self, user_id: uuid.UUID,
            old_password: str,
            new_password: str
    ) -> User:
        user = await self.get_by_id(user_id)
        if not verify_password(old_password, user.password):
            raise InvalidPasswordError()
        user.password = get_password_hash(new_password)
        await self.uow.commit()
        await self.uow.refresh(user)
        return user

    async def change_email(
            self, user_id: uuid.UUID,
            new_email: str,
            password: str
    ) -> User:
        user = await self.get_by_id(user_id)

        if new_email == user.email:
            return user

        if not verify_password(password, user.password):
            raise InvalidPasswordError()

        if not new_email.endswith("@ispras.ru"):
            raise EmailDomainNotAllowedError(email=new_email)

        existing_user = await self.uow.users.find_by_email(new_email)
        if existing_user:
            raise UserAlreadyExistsError(email=new_email)

        user.email = new_email
        user.username = new_email.rsplit("@", maxsplit=1)[0]
        await self.uow.commit()
        await self.uow.refresh(user)
        return user

    async def delete(self, user_id: uuid.UUID) -> None:
        user = await self.get_by_id(user_id)
        await self.uow.users.delete(user)
        await self.uow.commit()

    async def show_all(self) -> Sequence[User]:
        return await self.uow.users.list_all()
