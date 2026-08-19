from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from pathlib import Path

import aioboto3
import aiofiles
import aiofiles.os
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

NOT_FOUND_CODES = ("NoSuchKey", "NoSuchBucket", "404")


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    async def load(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def presigned_url(self, key: str, ttl_seconds: int) -> str | None: ...


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

    async def presigned_url(self, key: str, ttl_seconds: int) -> None:
        return None


class S3Storage(StorageBackend):
    def __init__(
        self,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str,
        endpoint_url: str | None = None,
        public_endpoint_url: str | None = None,
    ):
        self._bucket = bucket
        self._endpoint_url = endpoint_url
        self._public_endpoint_url = public_endpoint_url or endpoint_url
        self._session = aioboto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    @asynccontextmanager
    async def _client(self, public: bool = False):
        endpoint = self._public_endpoint_url if public else self._endpoint_url
        async with self._session.client(
            "s3", endpoint_url=endpoint, config=BotoConfig(signature_version="s3v4")
        ) as client:
            yield client

    async def save(self, key: str, data: bytes) -> None:
        async with self._client() as client:
            await client.put_object(Bucket=self._bucket, Key=key, Body=data)

    async def load(self, key: str) -> bytes:
        try:
            async with self._client() as client:
                response = await client.get_object(Bucket=self._bucket, Key=key)
                return await response["Body"].read()
        except ClientError as exc:
            if _error_code(exc) in NOT_FOUND_CODES:
                raise KeyError(key) from exc
            raise

    async def exists(self, key: str) -> bool:
        try:
            async with self._client() as client:
                await client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            if _error_code(exc) in NOT_FOUND_CODES:
                return False
            raise

    async def delete(self, key: str) -> None:
        if not await self.exists(key):
            raise KeyError(key)
        async with self._client() as client:
            await client.delete_object(Bucket=self._bucket, Key=key)

    async def presigned_url(self, key: str, ttl_seconds: int) -> str:
        async with self._client(public=True) as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=ttl_seconds,
            )
