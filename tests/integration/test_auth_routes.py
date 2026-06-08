import pytest
from fastapi import status

from tests.factories import make_user_create


def assert_error_response(response, status_code):
    assert response.status_code == status_code
    assert "message" in response.json()["error"]


@pytest.mark.asyncio(loop_scope="session")
async def test_register_success(client):
    user_data = make_user_create().model_dump(mode="json")
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert "password" not in body
    assert "id" in body
    assert "email" in body and body["email"] == user_data["email"]
    assert isinstance(body["id"], str)


@pytest.mark.asyncio(loop_scope="session")
async def test_register_duplicate(client, create_test_user):
    user_data = make_user_create().model_dump(mode="json")
    await create_test_user(email=user_data["email"])
    response = await client.post("/auth/register", json=user_data)
    assert_error_response(response, status.HTTP_409_CONFLICT)


@pytest.mark.parametrize("invalid_email", [
    "wrong.email@mail.ru",
    "wrong_email@gmail.com",
    "w.r.o.n.g_email@isp.ru",
    "wrong_e.m.a.i.l@ispras.com",
])
@pytest.mark.asyncio(loop_scope="session")
async def test_register_email_wrong_domain(client, invalid_email):
    user_data = make_user_create(email=invalid_email).model_dump(mode="json")
    response = await client.post("/auth/register", json=user_data)
    assert_error_response(response, status.HTTP_400_BAD_REQUEST)


@pytest.mark.asyncio(loop_scope="session")
async def test_login_success(client, create_test_user):
    password = "password"
    user = await create_test_user(email="test@ispras.ru", password=password)
    response = await client.post("/auth/login", data={
        "username": user.email,
        "password": password
    })
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "access_token" in body
    assert isinstance(body["access_token"], str)
    assert "token_type" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio(loop_scope="session")
async def test_login_wrong_password(client, create_test_user):
    user = await create_test_user(email="test@ispras.ru", password="password")
    response = await client.post("/auth/login", data={
        "username": user.email,
        "password": "another_password"
    })
    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.parametrize("invalid_email", [
    "another_email@ispras.ru",
    "wrong.email@mail.ru",
    "wrong_email@gmail.com",
    "w.r.o.n.g_email@isp.ru",
    "wrong_e.m.a.i.l@ispras.com",
])
@pytest.mark.asyncio(loop_scope="session")
async def test_login_wrong_email(client, create_test_user, invalid_email):
    password = "password"
    await create_test_user(email="test@ispras.ru", password=password)
    response = await client.post("/auth/login", data={
        "username": invalid_email,
        "password": password
    })
    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
