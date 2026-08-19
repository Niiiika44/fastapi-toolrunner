import pytest

from app.core.storage import StorageBackend

KEY = "1/file.yaml"
NESTED_KEY = "artifacts/42/memin.yaml"
MISSING_KEY = "no/such/key.yaml"
BINARY = b"\x00\xff\x10\x89PNG\r\n"


async def check_save_and_load(storage: StorageBackend) -> None:
    await storage.save(KEY, b"data")

    assert await storage.load(KEY) == b"data"


async def check_binary_content(storage: StorageBackend) -> None:
    await storage.save(KEY, BINARY)

    assert await storage.load(KEY) == BINARY


async def check_overwrite(storage: StorageBackend) -> None:
    await storage.save(KEY, b"first")
    await storage.save(KEY, b"second")

    assert await storage.load(KEY) == b"second"


async def check_nested_key(storage: StorageBackend) -> None:
    await storage.save(NESTED_KEY, b"data")

    assert await storage.load(NESTED_KEY) == b"data"
    assert await storage.exists(NESTED_KEY)


async def check_exists(storage: StorageBackend) -> None:
    assert not await storage.exists(KEY)
    await storage.save(KEY, b"data")

    assert await storage.exists(KEY)


async def check_delete(storage: StorageBackend) -> None:
    await storage.save(KEY, b"data")
    await storage.delete(KEY)

    assert not await storage.exists(KEY)


async def check_load_missing_raises_key_error(storage: StorageBackend) -> None:
    with pytest.raises(KeyError):
        await storage.load(MISSING_KEY)


async def check_delete_missing_raises_key_error(storage: StorageBackend) -> None:
    with pytest.raises(KeyError):
        await storage.delete(MISSING_KEY)


async def check_presigned_url(storage: StorageBackend, expect_url: bool) -> None:
    await storage.save(KEY, b"data")

    url = await storage.presigned_url(KEY, ttl_seconds=60)

    if expect_url:
        assert isinstance(url, str) and url.startswith("http")
    else:
        assert url is None
