import pytest
from fastapi import status
from sqlalchemy import select

from app.memory_allocator.models import TestArtifact
from tests.conftest import assert_error_response, make_zip


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_upload_success(
    client,
    create_test_user,
    auth_headers,
    example_correct_folder,
    db_session,
):
    user = await create_test_user()
    zip_bytes = make_zip(example_correct_folder)
    response = await client.post(
        "/upload/",
        files={"file": ("mips.zip", zip_bytes, "application/zip")},
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["platform"]["mmu_family"] == "mips_r6000"
    assert body["module_count"] == 1
    assert body["status"] == "parsed"
    test_id = body["id"]
    result = await db_session.execute(
        select(TestArtifact).where(TestArtifact.test_id == test_id)
    )
    assert len(result.scalars().all()) == 7


@pytest.mark.asyncio(loop_scope="session")
async def test_upload_no_user(client, example_correct_folder):
    zip_bytes = make_zip(example_correct_folder)
    response = await client.post(
        "/upload/",
        files={"file": ("mips.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
async def test_upload_not_zip(
    client,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    response = await client.post(
        "/upload/",
        files={"file": ("notazip.txt", b"some bytes", "text/plain")},
        headers=auth_headers(user),
    )
    assert_error_response(response, status.HTTP_400_BAD_REQUEST)
