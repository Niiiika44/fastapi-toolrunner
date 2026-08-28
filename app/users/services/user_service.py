import logging
from uuid import UUID

from app.auth.enums import Permission
from app.auth.hash_utils import get_password_hash, verify_password
from app.core.storage import StorageBackend, safe_delete
from app.core.unit_of_work import UnitOfWork
from app.users.enums import UserJobTitle
from app.users.exceptions import (
    EmailDomainNotAllowedError,
    InvalidPasswordError,
    RoleAlreadyAssignedError,
    RoleRequestConflictError,
    RoleRequestNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.users.models import User, UserPermission
from app.users.schemas import UserCreate, UserDomain, UserPermissionDomain, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, uow: UnitOfWork, storage: StorageBackend | None = None):
        self.uow = uow
        self.storage = storage

    async def find_by_id(self, user_id: UUID) -> User | None:
        return await self.uow.users.find_by_id(user_id)

    async def find_by_username(self, username: str) -> User | None:
        return await self.uow.users.find_by_username(username)

    async def find_by_email(self, email: str) -> User | None:
        return await self.uow.users.find_by_email(email)

    async def _get_entity(self, user_id: UUID) -> User:
        user = await self.uow.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(id=user_id)
        return user

    async def get_by_id(self, user_id: UUID) -> UserDomain:
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
            logger.warning("user.create_rejected", extra={"email": user_data.email})
            raise EmailDomainNotAllowedError(email=user_data.email)

        existing_user = await self.uow.users.find_by_email(user_data.email)
        if existing_user:
            logger.warning("user.create_rejected", extra={"email": user_data.email})
            raise UserAlreadyExistsError(email=user_data.email)

        username = user_data.email.rsplit("@", maxsplit=1)[0]
        hashed = get_password_hash(user_data.password)
        requested_role = user_data.job_title if user_data.job_title != UserJobTitle.OTHER else None
        new_user = User(**user_data.model_dump(exclude={"password", "job_title"}),
                        username=username,
                        password=hashed,
                        job_title=UserJobTitle.OTHER,
                        requested_job_title=requested_role)
        self.uow.users.add(new_user)
        await self.uow.commit()
        await self.uow.refresh(new_user)
        logger.info("user.created", extra={
            "user_id": str(new_user.id),
            "email": new_user.email
        })
        return UserDomain.model_validate(new_user)

    async def update(self, user_id: UUID, user_data: UserUpdate) -> UserDomain:
        user = await self._get_entity(user_id)
        for field, value in user_data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("user.updated", extra={
            "user_id": str(user_id),
            "field_names": list(user_data.model_dump(exclude_unset=True).keys())
        })
        return UserDomain.model_validate(user)

    async def change_password(
            self, user_id: UUID,
            old_password: str,
            new_password: str
    ) -> UserDomain:
        user = await self._get_entity(user_id)
        if not verify_password(old_password, user.password):
            raise InvalidPasswordError()
        user.password = get_password_hash(new_password)
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("user.password_changed", extra={
            "user_id": str(user_id)
        })
        return UserDomain.model_validate(user)

    async def change_email(
            self, user_id: UUID,
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
        logger.info("user.email_changed", extra={
            "user_id": str(user_id),
            "new_email": new_email,
            "old_email": old_email
        })
        return UserDomain.model_validate(user)

    async def delete(self, user_id: UUID) -> None:
        user = await self._get_entity(user_id)
        avatar_key = user.avatar_key
        await self.uow.users.delete(user)
        await self.uow.commit()
        if avatar_key is not None:
            await self._discard_avatar(avatar_key)
        logger.info("user.deleted", extra={"user_id": str(user_id)})

    async def _discard_avatar(self, avatar_key: str) -> None:
        if self.storage is None:
            logger.warning("user.avatar_not_discarded", extra={
                "storage_key": avatar_key,
                "reason": "service built without storage",
            })
            return
        await safe_delete(self.storage, avatar_key)

    async def show_all(self) -> list[UserDomain]:
        users = await self.uow.users.list_all()
        return [UserDomain.model_validate(user) for user in users]

    async def list_permissions(self, user_id: UUID) -> list[UserPermissionDomain]:
        user = await self._get_entity(user_id)
        return [UserPermissionDomain.model_validate(grant) for grant in user.permissions]

    async def grant_permission(self, user_id: UUID, permission: Permission) -> None:
        user = await self._get_entity(user_id)
        if any(grant.permission == permission for grant in user.permissions):
            logger.debug("user.permission_already_granted", extra={
                "user_id": str(user.id), "permission": permission
            })
            return
        user.permissions.append(UserPermission(permission=permission))
        await self.uow.commit()
        logger.info("user.permission_granted", extra={
            "user_id": str(user_id), "permission": permission
        })

    async def revoke_permission(self, user_id: UUID, permission: Permission) -> None:
        user = await self._get_entity(user_id)
        granted = next(
            (grant for grant in user.permissions if grant.permission == permission), None
        )
        if granted is None:
            logger.debug("user.permission_not_granted", extra={
                "user_id": str(user.id), "permission": permission
            })
            return
        user.permissions.remove(granted)
        await self.uow.commit()
        logger.info("user.permission_revoked", extra={
            "user_id": str(user_id), "permission": permission
        })

    async def set_superuser(self, email: str, is_superuser: bool = True) -> UserDomain:
        user = await self.find_by_email(email)
        if user is None:
            raise UserNotFoundError(email=email)
        user.is_superuser = is_superuser
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("user.superuser_changed", extra={
            "user_id": str(user.id), "is_superuser": is_superuser
        })
        return UserDomain.model_validate(user)

    async def request_role(self, user_id: UUID, job_title: UserJobTitle) -> UserDomain:
        user = await self._get_entity(user_id)
        current_role = user.job_title
        if user.job_title == job_title:
            raise RoleAlreadyAssignedError(user_id)
        user.requested_job_title = job_title
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("user.role_requested", extra={
            "user_id": str(user_id),
            "current_role": current_role,
            "requested_role": str(job_title)
        })
        return UserDomain.model_validate(user)

    async def list_role_requests(self) -> list[UserDomain]:
        users = await self.uow.users.list_with_role_requests()
        return [UserDomain.model_validate(user) for user in users]

    async def approve_role(self, user_id: UUID, expected: UserJobTitle) -> UserDomain:
        user = await self._get_entity(user_id)
        if user.requested_job_title is None:
            raise RoleRequestNotFoundError(user_id)
        if user.requested_job_title != expected:
            raise RoleRequestConflictError(user_id)
        user.job_title = expected
        user.requested_job_title = None
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("user.role_approved", extra={
            "user_id": str(user_id), "role_approved": str(expected)
        })
        return UserDomain.model_validate(user)

    async def reject_role(self, user_id: UUID) -> UserDomain:
        user = await self._get_entity(user_id)
        if user.requested_job_title is None:
            raise RoleRequestNotFoundError(user_id)
        user.requested_job_title = None
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("user.role_rejected", extra={"user_id": str(user_id)})
        return UserDomain.model_validate(user)

    async def withdraw_role_request(self, user_id: UUID) -> UserDomain:
        user = await self._get_entity(user_id)
        if user.requested_job_title is None:
            return UserDomain.model_validate(user)
        withdrawn = user.requested_job_title
        user.requested_job_title = None
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("user.role_request_withdrawn", extra={
            "user_id": str(user_id),
            "withdrawn_role": str(withdrawn),
        })
        return UserDomain.model_validate(user)

    async def set_role(self, user_id: UUID, job_title: UserJobTitle) -> UserDomain:
        user = await self._get_entity(user_id)
        user.job_title = job_title
        user.requested_job_title = None
        await self.uow.commit()
        await self.uow.refresh(user)
        logger.info("user.role_updated", extra={
            "user_id": str(user_id), "new_role": str(job_title)
        })
        return UserDomain.model_validate(user)
