import logging
import uuid

from app.auth.hash_utils import get_password_hash, verify_password
from app.core.unit_of_work import UnitOfWork
from app.users.exceptions import (
    EmailDomainNotAllowedError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.users.models import User
from app.users.schemas import UserCreate, UserDomain, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.uow.users.find_by_id(user_id)

    async def find_by_username(self, username: str) -> User | None:
        return await self.uow.users.find_by_username(username)

    async def find_by_email(self, email: str) -> User | None:
        return await self.uow.users.find_by_email(email)

    async def _get_entity(self, user_id: uuid.UUID) -> User:
        user = await self.uow.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(id=user_id)
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> UserDomain:
        return UserDomain.model_validate(await self._get_entity(user_id))

    async def get_by_username(self, username: str) -> UserDomain:
        user = await self.find_by_username(username)
        if not user:
            raise UserNotFoundError(username=username)
        return UserDomain.model_validate(user)

    async def get_by_email(self, email: str) -> UserDomain:
        user = await self.find_by_email(email)
        if not user:
            raise UserNotFoundError(email=email)
        return UserDomain.model_validate(user)

    async def create(self, user_data: UserCreate) -> UserDomain:
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
        logger.info("User created", extra={
            "event": "user_created",
            "user_id": str(new_user.id),
            "email": new_user.email
        })
        return UserDomain.model_validate(new_user)

    async def update(self, user_id: uuid.UUID, user_data: UserUpdate) -> UserDomain:
        user = await self._get_entity(user_id)
        for field, value in user_data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("User updated", extra={
            "event": "user_updated",
            "user_id": str(user.id),
            "fields": list(user_data.model_dump(exclude_unset=True).keys())
        })
        return UserDomain.model_validate(user)

    async def change_password(
            self, user_id: uuid.UUID,
            old_password: str,
            new_password: str
    ) -> UserDomain:
        user = await self._get_entity(user_id)
        if not verify_password(old_password, user.password):
            raise InvalidPasswordError()
        user.password = get_password_hash(new_password)
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("Password changed", extra={
            "event": "password_changed",
            "user_id": str(user.id)
        })
        return UserDomain.model_validate(user)

    async def change_email(
            self, user_id: uuid.UUID,
            new_email: str,
            password: str
    ) -> UserDomain:
        user = await self._get_entity(user_id)

        if new_email == user.email:
            return UserDomain.model_validate(user)

        if not verify_password(password, user.password):
            raise InvalidPasswordError()

        if not new_email.endswith("@ispras.ru"):
            raise EmailDomainNotAllowedError(email=new_email)

        existing_user = await self.uow.users.find_by_email(new_email)
        if existing_user:
            raise UserAlreadyExistsError(email=new_email)

        old_email = user.email
        user.email = new_email
        user.username = new_email.rsplit("@", maxsplit=1)[0]
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("Email changed", extra={
            "event": "email_changed",
            "user_id": str(user.id),
            "new_email": new_email,
            "old_email": old_email
        })
        return UserDomain.model_validate(user)

    async def delete(self, user_id: uuid.UUID) -> None:
        user = await self._get_entity(user_id)
        await self.uow.users.delete(user)
        await self.uow.commit()
        logger.info("User deleted", extra={
            "event": "user_deleted",
            "user_id": str(user.id)
        })

    async def show_all(self) -> list[UserDomain]:
        users = await self.uow.users.list_all()
        return [UserDomain.model_validate(user) for user in users]
