from fastapi import status
import pytest
import uuid

from starlette.status import HTTP_200_OK

from app.users.schemas import UserResponse


def assert_error_response(response, status_code):
    assert response.status_code == status_code
    assert "message" in response.json()["error"]


@pytest.mark.asyncio(loop_scope="session")
async def test_get_me_success(client, create_test_user, auth_headers):
    user = await create_test_user()
    headers = auth_headers(user)
    response = await client.get("/users/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "password" not in body
    assert body["email"] == user.email


@pytest.mark.asyncio(loop_scope="session")
async def test_get_me_no_token(client):
    response = await client.get("/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
async def test_get_users_success(client, create_test_user, auth_headers):
    admin_user = await create_test_user(is_superuser=True)
    headers = auth_headers(admin_user)
    ordinary_user = await create_test_user(
        email="nika@ispras.ru",
        first_name="Nika",
        last_name="Krit"
    )
    response = await client.get("/users", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 2
    admin_user_schema = UserResponse.model_validate(admin_user)
    ordinary_user_schema = UserResponse.model_validate(ordinary_user)
    assert admin_user_schema.model_dump(mode="json") in body
    assert ordinary_user_schema.model_dump(mode="json") in body


@pytest.mark.asyncio(loop_scope="session")
async def test_get_users_no_admin(client, create_test_user, auth_headers):
    user = await create_test_user()
    headers = auth_headers(user)
    response = await client.get("/users", headers=headers)
    assert_error_response(response, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_users_no_token(client):
    response = await client.get("/users")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
async def test_get_user_id_no_token(client):
    random_id = uuid.uuid4()
    response = await client.get(f"/users/{random_id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
async def test_get_user_id_nonexistent(client, create_test_user, auth_headers):
    random_id = uuid.uuid4()
    user = await create_test_user()
    headers = auth_headers(user)
    response = await client.get(f"/users/{random_id}", headers=headers)
    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_user_id_success(client, create_test_user, auth_headers):
    user = await create_test_user()
    headers = auth_headers(user)
    searched_user = await create_test_user(
        email="nika@ispras.ru",
        first_name="Nika",
        last_name="Krit"
    )
    response = await client.get(f"/users/{searched_user.id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["email"] == searched_user.email
    assert "password" not in body
    assert isinstance(body["id"], str)


