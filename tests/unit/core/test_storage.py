import pytest

from app.core.storage import LocalStorage
from tests.storage_contract import (
    check_binary_content,
    check_delete,
    check_delete_missing_raises_key_error,
    check_exists,
    check_load_missing_raises_key_error,
    check_nested_key,
    check_overwrite,
    check_presigned_url,
    check_save_and_load,
)


@pytest.mark.asyncio
async def test_save_and_load(tmp_path):
    await check_save_and_load(LocalStorage(tmp_path))


@pytest.mark.asyncio
async def test_binary_content(tmp_path):
    await check_binary_content(LocalStorage(tmp_path))


@pytest.mark.asyncio
async def test_overwrite(tmp_path):
    await check_overwrite(LocalStorage(tmp_path))


@pytest.mark.asyncio
async def test_nested_key(tmp_path):
    await check_nested_key(LocalStorage(tmp_path))


@pytest.mark.asyncio
async def test_exists(tmp_path):
    await check_exists(LocalStorage(tmp_path))


@pytest.mark.asyncio
async def test_delete(tmp_path):
    await check_delete(LocalStorage(tmp_path))


@pytest.mark.asyncio
async def test_load_missing_raises_key_error(tmp_path):
    await check_load_missing_raises_key_error(LocalStorage(tmp_path))


@pytest.mark.asyncio
async def test_delete_missing_raises_key_error(tmp_path):
    await check_delete_missing_raises_key_error(LocalStorage(tmp_path))


@pytest.mark.asyncio
async def test_presigned_url_is_not_supported(tmp_path):
    await check_presigned_url(LocalStorage(tmp_path), expect_url=False)


@pytest.mark.parametrize("malicious_key", [
    "../escape.yaml",
    "a/../../escape.yaml",
    "/etc/passwd",
])
@pytest.mark.asyncio
async def test_key_escapes_base(tmp_path, malicious_key):
    storage = LocalStorage(tmp_path)

    with pytest.raises(ValueError):
        await storage.save(malicious_key, b"\x00\xff\x10")
