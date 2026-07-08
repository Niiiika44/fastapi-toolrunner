import pytest
from fastapi import status

from tests.conftest import assert_error_response
from tests.factories import make_platform


@pytest.mark.asyncio(loop_scope="session")
async def test_list_all_success(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    platform_1 = make_platform(id=1)
    platform_2 = make_platform(id=2, mmu_family="armv7m", page_size=8)
    db_session.add_all([platform_1, platform_2])
    await db_session.commit()

    response = await client.get(
        "/platforms",
        headers=auth_headers(user),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 2
    pl_1, pl_2 = body[0], body[1]
    assert pl_1["created_at"] is not None
    assert pl_2["created_at"] is not None
    assert pl_1["id"] == 1 and pl_2["id"] == 2
    assert pl_1["config"] == pl_2["config"] == {}
    assert pl_1["mmu_family"] == "mips_r6000" and pl_2["mmu_family"] == "armv7m"
    assert pl_1["page_size"] == 4096 and pl_2["page_size"] == 8


@pytest.mark.asyncio(loop_scope="session")
async def test_list_all_no_user(client):
    response = await client.get("/platforms")

    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_platform_by_id_success(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    platform = make_platform(id=1)
    db_session.add(platform)
    await db_session.commit()

    response = await client.get(
        f"/platforms/{platform.id}",
        headers=auth_headers(user),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["created_at"] is not None
    assert body["id"] == 1
    assert body["config"] == {}
    assert body["mmu_family"] == "mips_r6000"
    assert body["page_size"] == 4096


@pytest.mark.asyncio(loop_scope="session")
async def test_get_platform_by_id_nonexistent_platform_id(
    client,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()

    response = await client.get(
        "/platforms/1",
        headers=auth_headers(user),
    )

    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_platform_by_id_no_user(client):
    response = await client.get("/platforms/1")

    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
