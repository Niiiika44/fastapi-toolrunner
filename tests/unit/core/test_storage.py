import pytest

from app.core.storage import LocalStorage

FILE_PATH_STR = "1/file.yaml"


@pytest.mark.asyncio
async def test_storage_success(tmp_path):
    storage = LocalStorage(tmp_path)
    await storage.save(FILE_PATH_STR, b"data")
    assert await storage.load(FILE_PATH_STR) == b"data"


@pytest.mark.asyncio
async def test_storage_exists(tmp_path):
    storage = LocalStorage(tmp_path)
    assert not await storage.exists(FILE_PATH_STR)
    await storage.save(FILE_PATH_STR, b"data")
    assert await storage.exists(FILE_PATH_STR)


@pytest.mark.asyncio
async def test_storage_delete(tmp_path):
    storage = LocalStorage(tmp_path)
    await storage.save(FILE_PATH_STR, b"data")
    assert await storage.exists(FILE_PATH_STR)
    await storage.delete(FILE_PATH_STR)
    assert not await storage.exists(FILE_PATH_STR)


@pytest.mark.asyncio
async def test_storage_load_nonexistent(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(KeyError):
        await storage.load("some_new_key")


@pytest.mark.asyncio
async def test_storage_delete_nonexistent(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(KeyError):
        await storage.delete("some_new_key")


@pytest.mark.asyncio
async def test_storage_binary_content(tmp_path):
    storage = LocalStorage(tmp_path)
    await storage.save(FILE_PATH_STR, b"\x00\xff\x10")
    assert await storage.load(FILE_PATH_STR) == b"\x00\xff\x10"


@pytest.mark.parametrize("malicious_key", [
    "../escape.yaml",
    "a/../../escape.yaml",
    "/etc/passwd",
])
@pytest.mark.asyncio
async def test_storage_key_escapes_base(tmp_path, malicious_key):
    storage = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        await storage.save(malicious_key, b"\x00\xff\x10")
