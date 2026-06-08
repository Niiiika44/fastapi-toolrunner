import uuid

import pytest
from fastapi import status

from app.users.schemas import UserResponse
from tests.conftest import assert_error_response
from tests.factories import DEFAULT_PASSWORD


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
async def test_get_user_id_success(client, create_test_user, auth_headers):
    user = await create_test_user()
    headers = auth_headers(user)
    response = await client.get(f"/users/{user.id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == user.email


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
async def test_patch_me_success(client, create_test_user, auth_headers):
    user = await create_test_user()
    headers = auth_headers(user)
    update_data = {"first_name": "Nika", "last_name": "Krit"}
    response = await client.patch(f"/users/{user.id}", headers=headers, json=update_data)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "password" not in body
    assert body["email"] == user.email
    assert body["first_name"] == update_data["first_name"]
    assert body["last_name"] == update_data["last_name"]


@pytest.mark.asyncio(loop_scope="session")
async def test_patch_admin_success(client, create_test_user, auth_headers):
    admin = await create_test_user(is_superuser=True)
    ordinary_user = await create_test_user(email="new_email@ispras.ru")
    headers = auth_headers(admin)
    update_data = {"first_name": "Nika", "last_name": "Krit"}
    response = await client.patch(f"/users/{ordinary_user.id}", headers=headers, json=update_data)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "password" not in body
    assert body["email"] == ordinary_user.email
    assert body["first_name"] == update_data["first_name"]
    assert body["last_name"] == update_data["last_name"]
    assert admin.first_name != update_data["first_name"]
    assert admin.last_name != update_data["last_name"]


@pytest.mark.asyncio(loop_scope="session")
async def test_patch_stranger(client, create_test_user, auth_headers):
    user = await create_test_user(email="new_email@ispras.ru")
    stranger_id = uuid.uuid4()
    headers = auth_headers(user)
    update_data = {"first_name": "Nika", "last_name": "Krit"}
    response = await client.patch(f"/users/{stranger_id}", headers=headers, json=update_data)
    assert_error_response(response, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
async def test_change_password_success(client, create_test_user, auth_headers):
    user = await create_test_user()
    headers = auth_headers(user)
    update_data = {
        "old_password": DEFAULT_PASSWORD,
        "new_password": "new_password"
    }
    response = await client.post(
        f"/users/{user.id}/change-password", headers=headers, json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "password" not in body
    assert body["email"] == user.email
    assert body["first_name"] == user.first_name
    assert body["last_name"] == user.last_name


@pytest.mark.asyncio(loop_scope="session")
async def test_change_password_stranger_failure(client, create_test_user, auth_headers):
    user = await create_test_user()
    random_id = uuid.uuid4()
    headers = auth_headers(user)
    update_data = {
        "old_password": DEFAULT_PASSWORD,
        "new_password": "new_password"
    }
    response = await client.post(
        f"/users/{random_id}/change-password", headers=headers, json=update_data
    )
    assert_error_response(response, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
async def test_change_password_admin_failure(client, create_test_user, auth_headers):
    user = await create_test_user(is_superuser=True)
    random_id = uuid.uuid4()
    headers = auth_headers(user)
    update_data = {
        "old_password": DEFAULT_PASSWORD,
        "new_password": "new_password"
    }
    response = await client.post(
        f"/users/{random_id}/change-password", headers=headers, json=update_data
    )
    assert_error_response(response, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
async def test_change_email_success(client, create_test_user, auth_headers):
    user = await create_test_user()
    headers = auth_headers(user)
    update_data = {
        "password": DEFAULT_PASSWORD,
        "new_email": "new_email@ispras.ru"
    }
    response = await client.post(
        f"/users/{user.id}/change-email", headers=headers, json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "password" not in body
    assert body["email"] == update_data["new_email"]
    assert body["first_name"] == user.first_name
    assert body["last_name"] == user.last_name


@pytest.mark.asyncio(loop_scope="session")
async def test_change_email_stranger_failure(client, create_test_user, auth_headers):
    user = await create_test_user()
    random_id = uuid.uuid4()
    headers = auth_headers(user)
    update_data = {
        "password": DEFAULT_PASSWORD,
        "new_email": "new_email@ispras.ru"
    }
    response = await client.post(
        f"/users/{random_id}/change-email", headers=headers, json=update_data
    )
    assert_error_response(response, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
async def test_change_email_admin_failure(client, create_test_user, auth_headers):
    user = await create_test_user(is_superuser=True)
    random_id = uuid.uuid4()
    headers = auth_headers(user)
    update_data = {
        "password": DEFAULT_PASSWORD,
        "new_email": "new_email@ispras.ru"
    }
    response = await client.post(
        f"/users/{random_id}/change-email", headers=headers, json=update_data
    )
    assert_error_response(response, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
async def test_change_email_same_value(client, create_test_user, auth_headers):
    user = await create_test_user()
    headers = auth_headers(user)
    update_data = {
        "password": DEFAULT_PASSWORD,
        "new_email": user.email
    }
    response = await client.post(
        f"/users/{user.id}/change-email", headers=headers, json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "password" not in body
    assert body["email"] == update_data["new_email"]
    assert body["first_name"] == user.first_name
    assert body["last_name"] == user.last_name


@pytest.mark.parametrize("invalid_email", [
    "wrong.email@mail.ru",
    "wrong_email@gmail.com",
    "w.r.o.n.g_email@isp.ru",
    "wrong_e.m.a.i.l@ispras.com",
])
@pytest.mark.asyncio(loop_scope="session")
async def test_change_email_incorrect_domain(client, create_test_user, auth_headers, invalid_email):
    user = await create_test_user()
    headers = auth_headers(user)
    update_data = {
        "password": DEFAULT_PASSWORD,
        "new_email": invalid_email
    }
    response = await client.post(
        f"/users/{user.id}/change-email", headers=headers, json=update_data
    )
    assert_error_response(response, status.HTTP_400_BAD_REQUEST)


@pytest.mark.asyncio(loop_scope="session")
async def test_change_email_incorrect_password(client, create_test_user, auth_headers):
    user = await create_test_user()
    headers = auth_headers(user)
    update_data = {
        "password": "wrong_password",
        "new_email": "new_email@ispras.ru"
    }
    response = await client.post(
        f"/users/{user.id}/change-email", headers=headers, json=update_data
    )
    assert_error_response(response, status.HTTP_400_BAD_REQUEST)


@pytest.mark.asyncio(loop_scope="session")
async def test_change_email_taken(client, create_test_user, auth_headers):
    user = await create_test_user()
    another_user = await create_test_user(email="taken_email@ispras.ru")
    headers = auth_headers(user)
    update_data = {
        "password": DEFAULT_PASSWORD,
        "new_email": another_user.email
    }
    response = await client.post(
        f"/users/{user.id}/change-email", headers=headers, json=update_data
    )
    assert_error_response(response, status.HTTP_409_CONFLICT)


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_user_success(client, create_test_user, auth_headers):
    user = await create_test_user()
    headers = auth_headers(user)
    response = await client.delete(f"/users/{user.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_user_no_token(client, create_test_user):
    user = await create_test_user()
    response = await client.delete(f"/users/{user.id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_admin_success(client, create_test_user, auth_headers):
    user = await create_test_user(email="new_email@ispras.ru")
    admin = await create_test_user(is_superuser=True)
    headers = auth_headers(admin)
    response = await client.delete(f"/users/{user.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_stranger(client, create_test_user, auth_headers):
    user = await create_test_user(email="new_email@ispras.ru")
    stranger = await create_test_user()
    headers = auth_headers(user)
    response = await client.delete(f"/users/{stranger.id}", headers=headers)
    assert_error_response(response, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_nonexistent(client, create_test_user, auth_headers):
    user = await create_test_user(is_superuser=True)
    random_id = uuid.uuid4()
    headers = auth_headers(user)
    response = await client.delete(f"/users/{random_id}", headers=headers)
    assert_error_response(response, status.HTTP_404_NOT_FOUND)
