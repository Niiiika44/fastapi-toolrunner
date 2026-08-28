import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.storage import StorageBackend, safe_delete
from app.core.unit_of_work import UnitOfWork
from app.users.avatar_image import OUTPUT_EXTENSION, encode_avatar
from app.users.exceptions import AvatarNotFoundError, AvatarTooLargeError, UserNotFoundError
from app.users.models import User
from app.users.schemas import AvatarContentDomain, AvatarLinkDomain, UserDomain

logger = logging.getLogger(__name__)

settings = get_settings()

_CHUNK_SIZE = 64 * 1024


class AvatarService:
    def __init__(self, uow: UnitOfWork, storage: StorageBackend):
        self.uow = uow
        self.storage = storage

    @staticmethod
    def storage_key(user_id: UUID) -> str:
        return f"avatars/{user_id}.{OUTPUT_EXTENSION}"

    async def _get_entity(self, user_id: UUID) -> User:
        user = await self.uow.users.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(id=user_id)
        return user

    async def set_avatar(self, user_id: UUID, file: UploadFile) -> UserDomain:
        user = await self._get_entity(user_id)

        raw = await self._read_within_limit(file)
        image = await run_in_threadpool(encode_avatar, raw)

        key = self.storage_key(user_id)
        had_avatar = user.avatar_key is not None

        await self.storage.save(key, image)
        user.avatar_key = key
        user.avatar_updated_at = datetime.now(UTC)
        try:
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            if not had_avatar:
                await safe_delete(self.storage, key)
            raise

        logger.info("user.avatar_updated", extra={
            "user_id": str(user_id),
            "storage_key": key,
            "source_bytes": len(raw),
            "stored_bytes": len(image),
        })
        return UserDomain.model_validate(user)

    async def delete_avatar(self, user_id: UUID) -> None:
        user = await self._get_entity(user_id)
        key = user.avatar_key
        if key is None:
            return

        user.avatar_key = None
        user.avatar_updated_at = None
        await self.uow.commit()

        await safe_delete(self.storage, key)
        logger.info("user.avatar_deleted", extra={"user_id": str(user_id), "storage_key": key})

    async def get_avatar(self, user_id: UUID) -> AvatarLinkDomain | AvatarContentDomain:
        user = await self.uow.users.find_by_id(user_id)
        if user is None or user.avatar_key is None:
            raise AvatarNotFoundError()

        url = await self.storage.presigned_url(user.avatar_key, settings.S3_PRESIGN_TTL_SECONDS)
        if url is not None:
            return AvatarLinkDomain(url=url)

        try:
            content = await self.storage.load(user.avatar_key)
        except KeyError as exc:
            raise AvatarNotFoundError() from exc
        return AvatarContentDomain(content=content)

    async def _read_within_limit(self, file: UploadFile) -> bytes:
        limit = settings.AVATAR_MAX_BYTES
        chunks: list[bytes] = []
        total = 0
        while chunk := await file.read(_CHUNK_SIZE):
            total += len(chunk)
            if total > limit:
                raise AvatarTooLargeError(limit)
            chunks.append(chunk)
        return b"".join(chunks)
