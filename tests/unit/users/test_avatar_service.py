import io
import uuid
from datetime import UTC, datetime

import pytest
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app.core.config import get_settings
from app.users.exceptions import (
    AvatarNotFoundError,
    AvatarTooLargeError,
    UnsupportedImageError,
    UserNotFoundError,
)
from app.users.schemas import AvatarContentDomain, AvatarLinkDomain, UserDomain
from app.users.services import AvatarService
from tests.factories import make_image_bytes, make_user

settings = get_settings()


def upload(payload: bytes, filename: str = "photo.png") -> UploadFile:
    return UploadFile(
        file=io.BytesIO(payload),
        filename=filename,
        headers=Headers({"content-type": "image/png"}),
    )


@pytest.fixture
def user():
    return make_user(avatar_key=None, avatar_updated_at=None)


@pytest.mark.asyncio
async def test_set_avatar_stores_and_records(mock_uow, mock_storage, user):
    mock_uow.users.find_by_id.return_value = user
    service = AvatarService(mock_uow, mock_storage)

    result = await service.set_avatar(user.id, upload(make_image_bytes()))

    assert isinstance(result, UserDomain)
    assert user.avatar_key == f"avatars/{user.id}.webp"
    assert user.avatar_updated_at is not None
    mock_storage.save.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_avatar_stores_reencoded_bytes(mock_uow, mock_storage, user):
    mock_uow.users.find_by_id.return_value = user
    service = AvatarService(mock_uow, mock_storage)

    await service.set_avatar(user.id, upload(make_image_bytes(width=1200, height=900)))

    _, stored = mock_storage.save.await_args.args
    image = Image.open(io.BytesIO(stored))
    assert image.format == "WEBP"
    assert image.size == (settings.AVATAR_SIZE_PX, settings.AVATAR_SIZE_PX)


@pytest.mark.asyncio
async def test_set_avatar_rejects_unsupported_before_touching_storage(
    mock_uow, mock_storage, user
):
    mock_uow.users.find_by_id.return_value = user
    service = AvatarService(mock_uow, mock_storage)

    with pytest.raises(UnsupportedImageError):
        await service.set_avatar(user.id, upload(b"%PDF-1.7" + b"\x00" * 64))

    mock_storage.save.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_avatar_rejects_oversized_file(mock_uow, mock_storage, user):
    mock_uow.users.find_by_id.return_value = user
    service = AvatarService(mock_uow, mock_storage)
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (settings.AVATAR_MAX_BYTES + 1)

    with pytest.raises(AvatarTooLargeError):
        await service.set_avatar(user.id, upload(oversized))

    mock_storage.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_avatar_for_missing_user(mock_uow, mock_storage):
    mock_uow.users.find_by_id.return_value = None
    service = AvatarService(mock_uow, mock_storage)

    with pytest.raises(UserNotFoundError):
        await service.set_avatar(uuid.uuid4(), upload(make_image_bytes()))

    mock_storage.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_replacing_reuses_the_key_and_bumps_the_version(mock_uow, mock_storage, user):
    mock_uow.users.find_by_id.return_value = user
    service = AvatarService(mock_uow, mock_storage)

    first = await service.set_avatar(user.id, upload(make_image_bytes()))
    user.avatar_updated_at = user.avatar_updated_at.replace(year=2020)
    stale_url = UserDomain.model_validate(user).avatar_url
    second = await service.set_avatar(user.id, upload(make_image_bytes(width=300, height=300)))

    keys = {call.args[0] for call in mock_storage.save.await_args_list}
    assert keys == {f"avatars/{user.id}.webp"}
    mock_storage.delete.assert_not_awaited()
    assert first.avatar_url is not None
    assert second.avatar_url != stale_url


@pytest.mark.asyncio
async def test_commit_failure_removes_a_freshly_written_object(mock_uow, mock_storage, user):
    mock_uow.users.find_by_id.return_value = user
    mock_uow.commit.side_effect = RuntimeError("commit failed")
    service = AvatarService(mock_uow, mock_storage)

    with pytest.raises(RuntimeError):
        await service.set_avatar(user.id, upload(make_image_bytes()))

    mock_uow.rollback.assert_awaited_once()
    mock_storage.delete.assert_awaited_once_with(f"avatars/{user.id}.webp")


@pytest.mark.asyncio
async def test_commit_failure_keeps_an_existing_object(mock_uow, mock_storage):
    user = make_user(avatar_key="avatars/old.webp", avatar_updated_at=datetime.now(UTC))
    mock_uow.users.find_by_id.return_value = user
    mock_uow.commit.side_effect = RuntimeError("commit failed")
    service = AvatarService(mock_uow, mock_storage)

    with pytest.raises(RuntimeError):
        await service.set_avatar(user.id, upload(make_image_bytes()))

    mock_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_avatar_clears_columns_and_object(mock_uow, mock_storage):
    key = "avatars/x.webp"
    user = make_user(avatar_key=key, avatar_updated_at=datetime.now(UTC))
    mock_uow.users.find_by_id.return_value = user
    service = AvatarService(mock_uow, mock_storage)

    await service.delete_avatar(user.id)

    assert user.avatar_key is None
    assert user.avatar_updated_at is None
    mock_uow.commit.assert_awaited_once()
    mock_storage.delete.assert_awaited_once_with(key)


@pytest.mark.asyncio
async def test_delete_avatar_is_idempotent(mock_uow, mock_storage, user):
    mock_uow.users.find_by_id.return_value = user
    service = AvatarService(mock_uow, mock_storage)

    await service.delete_avatar(user.id)

    mock_uow.commit.assert_not_awaited()
    mock_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_avatar_survives_a_storage_failure(mock_uow, mock_storage):
    user = make_user(avatar_key="avatars/x.webp", avatar_updated_at=datetime.now(UTC))
    mock_uow.users.find_by_id.return_value = user
    mock_storage.delete.side_effect = RuntimeError("storage is down")
    service = AvatarService(mock_uow, mock_storage)

    await service.delete_avatar(user.id)

    assert user.avatar_key is None


@pytest.mark.asyncio
async def test_get_avatar_prefers_a_link(mock_uow, mock_storage):
    user = make_user(avatar_key="avatars/x.webp", avatar_updated_at=datetime.now(UTC))
    mock_uow.users.find_by_id.return_value = user
    mock_storage.presigned_url.return_value = "https://s3.example/avatars/x.webp?sig"
    service = AvatarService(mock_uow, mock_storage)

    result = await service.get_avatar(user.id)

    assert isinstance(result, AvatarLinkDomain)
    mock_storage.load.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_avatar_falls_back_to_bytes(mock_uow, mock_storage):
    user = make_user(avatar_key="avatars/x.webp", avatar_updated_at=datetime.now(UTC))
    mock_uow.users.find_by_id.return_value = user
    mock_storage.presigned_url.return_value = None
    mock_storage.load.return_value = b"webp-bytes"
    service = AvatarService(mock_uow, mock_storage)

    result = await service.get_avatar(user.id)

    assert isinstance(result, AvatarContentDomain)
    assert result.content == b"webp-bytes"


@pytest.mark.asyncio
async def test_get_avatar_hides_whether_the_user_exists(mock_uow, mock_storage, user):
    service = AvatarService(mock_uow, mock_storage)

    mock_uow.users.find_by_id.return_value = None
    with pytest.raises(AvatarNotFoundError) as missing_user:
        await service.get_avatar(uuid.uuid4())

    mock_uow.users.find_by_id.return_value = user
    with pytest.raises(AvatarNotFoundError) as no_avatar:
        await service.get_avatar(user.id)

    assert str(missing_user.value) == str(no_avatar.value)


@pytest.mark.asyncio
async def test_get_avatar_when_the_object_vanished(mock_uow, mock_storage):
    user = make_user(avatar_key="avatars/x.webp", avatar_updated_at=datetime.now(UTC))
    mock_uow.users.find_by_id.return_value = user
    mock_storage.presigned_url.return_value = None
    mock_storage.load.side_effect = KeyError("avatars/x.webp")
    service = AvatarService(mock_uow, mock_storage)

    with pytest.raises(AvatarNotFoundError):
        await service.get_avatar(user.id)
