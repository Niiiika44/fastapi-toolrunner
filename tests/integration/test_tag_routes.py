from app.memory_allocator.models import Tag
import pytest
from fastapi import status
from sqlalchemy import select

from app.memory_allocator.schemas import TagCreate
from tests.conftest import assert_error_response
from tests.factories import make_tag


@pytest.mark.asyncio(loop_scope="session")
async def test_create_tag_success(
    client,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    tag_data = TagCreate(name="low_ram").model_dump()

    response = await client.post(
        "/tags",
        json=tag_data,
        headers=auth_headers(user),
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["id"] is not None
    assert body["name"] == tag_data["name"]


@pytest.mark.asyncio(loop_scope="session")
async def test_create_tag_duplicated(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    tag_existing = make_tag(name="low_ram")
    db_session.add(tag_existing)
    await db_session.commit()
    tag_data = TagCreate(name="low_ram").model_dump()

    response = await client.post(
        "/tags",
        json=tag_data,
        headers=auth_headers(user),
    )

    assert_error_response(response, status.HTTP_409_CONFLICT)


@pytest.mark.asyncio(loop_scope="session")
async def test_create_tag_no_user(client):
    response = await client.post("/tags")
    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.asyncio(loop_scope="session")
async def test_list_all_success(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    tag_1 = make_tag(name="low_ram")
    tag_2 = make_tag(id=2, name="high_ram")
    db_session.add_all([tag_1, tag_2])
    await db_session.commit()

    response = await client.get(
        "/tags",
        headers=auth_headers(user),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 2
    assert {t["id"] for t in body} == {1, 2}
    assert {t["name"] for t in body} == {"low_ram", "high_ram"}


@pytest.mark.asyncio(loop_scope="session")
async def test_list_all_empty_success(
    client,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()

    response = await client.get(
        "/tags",
        headers=auth_headers(user),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_list_all_no_user(client):
    response = await client.get("/tags")
    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_tag_success(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    tag = make_tag(name="low_ram")
    db_session.add(tag)
    await db_session.commit()

    response = await client.get(
        f"/tags/{tag.id}",
        headers=auth_headers(user),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == tag.id
    assert body["name"] == tag.name


@pytest.mark.asyncio(loop_scope="session")
async def test_get_tag_nonexisting_tag(
    client,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()

    response = await client.get(
        "/tags/1",
        headers=auth_headers(user),
    )

    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_tag_no_user(client):
    response = await client.get("/tags/1")
    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_success(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    tag = make_tag(name="low_ram")
    db_session.add(tag)
    await db_session.commit()

    response = await client.delete(
        f"/tags/{tag.id}",
        headers=auth_headers(user),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    query = select(Tag).where(Tag.id == tag.id)
    result = await db_session.execute(query)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_nonexisting_tag(
    client,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()

    response = await client.delete(
        "/tags/1",
        headers=auth_headers(user),
    )

    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_no_user(client):
    response = await client.delete("/tags/1")
    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
