import pytest
from fastapi import status

from app.memory_allocator.enums import TestStatus
from tests.conftest import assert_error_response, make_zip
from tests.factories import make_tag, make_test


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_upload_success(
    client,
    create_test_user,
    auth_headers,
    example_correct_folder,
    override_dispatch,
):
    user = await create_test_user()
    zip_bytes = make_zip(example_correct_folder)
    response = await client.post(
        "/tests/upload",
        files={"file": ("mips.zip", zip_bytes, "application/zip")},
        headers=auth_headers(user),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    body = response.json()
    assert body["status"] == TestStatus.PENDING
    assert body["platform"]["mmu_family"] == "mips_r6000"
    assert body["module_count"] == 0
    assert body["uploaded_by"]["email"] == user.email
    override_dispatch.assert_called_once_with(body["id"])


@pytest.mark.asyncio(loop_scope="session")
async def test_upload_no_user(client, example_correct_folder):
    zip_bytes = make_zip(example_correct_folder)
    response = await client.post(
        "/tests/upload",
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
        "/tests/upload",
        files={"file": ("notazip.txt", b"some bytes", "text/plain")},
        headers=auth_headers(user),
    )
    assert_error_response(response, status.HTTP_400_BAD_REQUEST)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
@pytest.mark.usefixtures("override_dispatch")
async def test_list_tests_success(
    client,
    create_test_user,
    auth_headers,
    example_correct_folder,
):
    user = await create_test_user()
    zip_bytes = make_zip(example_correct_folder)
    headers = auth_headers(user)
    await client.post(
        "/tests/upload",
        files={"file": ("mips.zip", zip_bytes, "application/zip")},
        headers=headers,
    )
    await client.post(
        "/tests/upload",
        files={"file": ("mips2.zip", zip_bytes, "application/zip")},
        headers=headers,
    )
    response = await client.get(
        "/tests",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 2
    assert "uploaded_by" in body[0]
    assert "email" in body[0]["uploaded_by"]
    assert body[0]["uploaded_by"]["email"] == user.email
    assert "platform" in body[1]
    assert "mmu_family" in body[1]["platform"]
    assert body[1]["platform"]["mmu_family"] == "mips_r6000"


@pytest.mark.asyncio(loop_scope="session")
async def test_list_tests_no_user(
    client,
):
    response = await client.get(
        "/tests"
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
async def test_attach_tag_success(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    test = make_test(tags=[], uploaded_by=user)
    tag = make_tag(tests=[])
    db_session.add_all([test, tag])
    await db_session.commit()

    response = await client.post(
        f"/tests/{test.id}/tags/{tag.id}",
        headers=auth_headers(user),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert test in tag.tests
    assert tag in test.tags


@pytest.mark.asyncio(loop_scope="session")
async def test_attach_tag_success_idempotency(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    test = make_test(tags=[], uploaded_by=user)
    tag = make_tag(tests=[])
    db_session.add_all([test, tag])
    await db_session.commit()

    response_1 = await client.post(
        f"/tests/{test.id}/tags/{tag.id}",
        headers=auth_headers(user),
    )
    response_2 = await client.post(
        f"/tests/{test.id}/tags/{tag.id}",
        headers=auth_headers(user),
    )

    assert response_1.status_code == status.HTTP_204_NO_CONTENT
    assert response_2.status_code == status.HTTP_204_NO_CONTENT
    assert test in tag.tests
    assert tag in test.tags


@pytest.mark.asyncio(loop_scope="session")
async def test_attach_tag_no_user(client):
    response = await client.post("/tests/1/tags/1")
    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.asyncio(loop_scope="session")
async def test_detach_tag_success(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    test = make_test(tags=[], uploaded_by=user)
    tag = make_tag(tests=[test])
    db_session.add_all([test, tag])
    await db_session.commit()

    response = await client.delete(
        f"/tests/{test.id}/tags/{tag.id}",
        headers=auth_headers(user),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert test not in tag.tests
    assert tag not in test.tags


@pytest.mark.asyncio(loop_scope="session")
async def test_detach_tag_nonexisting_test(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    tag = make_tag(tests=[])
    db_session.add(tag)
    await db_session.commit()

    response = await client.delete(
        f"/tests/1/tags/{tag.id}",
        headers=auth_headers(user),
    )

    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
async def test_detach_tag_nonexisting_tag(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    test = make_test(tags=[], uploaded_by=user)
    db_session.add(test)
    await db_session.commit()

    response = await client.delete(
        f"/tests/{test.id}/tags/1",
        headers=auth_headers(user),
    )

    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
async def test_detach_tag_no_user(client):
    response = await client.delete("/tests/1/tags/1")
    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
