from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles
import aiofiles.os


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    async def load(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...


class LocalStorage(StorageBackend):
    def __init__(self, base_path: Path):
        self.base_path = base_path

    def _full_path(self, key: str) -> Path:
        full_path = (self.base_path / key).resolve()
        if not full_path.is_relative_to(self.base_path.resolve()):
            raise ValueError(f"Storage key escapes base path: {key}")
        return full_path

    async def save(self, key: str, data: bytes) -> None:
        full_path = self._full_path(key)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(full_path, mode="wb") as f:
            await f.write(data)

    async def load(self, key: str) -> bytes:
        full_path = self._full_path(key)
        try:
            async with aiofiles.open(full_path, "rb") as f:
                return await f.read()
        except FileNotFoundError as e:
            raise KeyError(key) from e

    async def delete(self, key: str) -> None:
        full_path = self._full_path(key)
        try:
            await aiofiles.os.remove(full_path)
        except FileNotFoundError as e:
            raise KeyError(key) from e

    async def exists(self, key: str) -> bool:
        full_path = self._full_path(key)
        return await aiofiles.os.path.exists(full_path)
