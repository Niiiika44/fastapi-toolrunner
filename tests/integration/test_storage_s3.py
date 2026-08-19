from collections.abc import AsyncGenerator, Generator
from urllib.parse import parse_qs, urlsplit

import aioboto3
import httpx
import pytest
import pytest_asyncio
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from app.core.storage import S3Storage
from tests.storage_contract import (
    KEY,
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

ACCESS_KEY = "testaccess"
SECRET_KEY = "testsecret123"
BUCKET = "contract"
TTL = 60


@pytest.fixture(scope="session")
def minio_endpoint() -> Generator[str, None, None]:
    container = (
        DockerContainer("minio/minio:latest")
        .with_command("server /data")
        .with_env("MINIO_ROOT_USER", ACCESS_KEY)
        .with_env("MINIO_ROOT_PASSWORD", SECRET_KEY)
        .with_exposed_ports(9000)
    )
    with container:
        wait_for_logs(container, "API:", timeout=60)
        host = container.get_container_host_ip()
        port = container.get_exposed_port(9000)
        yield f"http://{host}:{port}"


@pytest_asyncio.fixture(loop_scope="session")
async def s3_storage(minio_endpoint) -> AsyncGenerator[S3Storage, None]:
    session = aioboto3.Session(
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",
    )
    async with session.client("s3", endpoint_url=minio_endpoint) as client:
        try:
            await client.create_bucket(Bucket=BUCKET)
        except client.exceptions.BucketAlreadyOwnedByYou:
            pass
        objects = await client.list_objects_v2(Bucket=BUCKET)
        for obj in objects.get("Contents", []):
            await client.delete_object(Bucket=BUCKET, Key=obj["Key"])

    yield S3Storage(
        bucket=BUCKET,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        region="us-east-1",
        endpoint_url=minio_endpoint,
        public_endpoint_url=minio_endpoint,
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_save_and_load(s3_storage):
    await check_save_and_load(s3_storage)


@pytest.mark.asyncio(loop_scope="session")
async def test_binary_content(s3_storage):
    await check_binary_content(s3_storage)


@pytest.mark.asyncio(loop_scope="session")
async def test_overwrite(s3_storage):
    await check_overwrite(s3_storage)


@pytest.mark.asyncio(loop_scope="session")
async def test_nested_key(s3_storage):
    await check_nested_key(s3_storage)


@pytest.mark.asyncio(loop_scope="session")
async def test_exists(s3_storage):
    await check_exists(s3_storage)


@pytest.mark.asyncio(loop_scope="session")
async def test_delete(s3_storage):
    await check_delete(s3_storage)


@pytest.mark.asyncio(loop_scope="session")
async def test_load_missing_raises_key_error(s3_storage):
    await check_load_missing_raises_key_error(s3_storage)


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_missing_raises_key_error(s3_storage):
    await check_delete_missing_raises_key_error(s3_storage)


@pytest.mark.asyncio(loop_scope="session")
async def test_presigned_url_is_supported(s3_storage):
    await check_presigned_url(s3_storage, expect_url=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_presigned_url_signs_public_endpoint(s3_storage, minio_endpoint):
    await s3_storage.save(KEY, b"data")

    url = await s3_storage.presigned_url(KEY, ttl_seconds=TTL)

    parsed = urlsplit(url)
    assert f"{parsed.scheme}://{parsed.netloc}" == minio_endpoint
    assert parse_qs(parsed.query)["X-Amz-Expires"] == [str(TTL)]


@pytest.mark.asyncio(loop_scope="session")
async def test_presigned_url_downloads_without_credentials(s3_storage):
    await s3_storage.save(KEY, b"payload-for-link")

    url = await s3_storage.presigned_url(KEY, ttl_seconds=TTL)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.content == b"payload-for-link"
