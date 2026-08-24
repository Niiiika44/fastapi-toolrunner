import pytest
from fastapi import status

from app.auth.enums import Permission
from app.users.enums import UserJobTitle

GRANT = f"/users/{{user_id}}/permissions/{Permission.TEST_UPLOAD}"


@pytest.mark.asyncio(loop_scope="session")
async def test_superuser_grants_a_permission(client, create_test_user, auth_headers):
    admin = await create_test_user(email="admin@ispras.ru", is_superuser=True)
    user = await create_test_user(email="user@ispras.ru", job_title=UserJobTitle.ANALYST)

    granted = await client.post(GRANT.format(user_id=user.id), headers=auth_headers(admin))
    listed = await client.get(f"/users/{user.id}/permissions", headers=auth_headers(admin))

    assert granted.status_code == status.HTTP_204_NO_CONTENT
    assert [row["permission"] for row in listed.json()] == [Permission.TEST_UPLOAD]
    assert listed.json()[0]["granted_at"]


@pytest.mark.asyncio(loop_scope="session")
async def test_the_grant_actually_opens_the_gate(client, create_test_user, auth_headers):
    admin = await create_test_user(email="admin@ispras.ru", is_superuser=True)
    user = await create_test_user(email="user@ispras.ru", job_title=UserJobTitle.ANALYST)
    upload = {"files": {"file": ("case.zip", b"not a zip", "application/zip")}}

    before = await client.post("/tests/upload", headers=auth_headers(user), **upload)
    await client.post(GRANT.format(user_id=user.id), headers=auth_headers(admin))
    after = await client.post("/tests/upload", headers=auth_headers(user), **upload)

    assert before.status_code == status.HTTP_403_FORBIDDEN
    assert after.status_code != status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio(loop_scope="session")
async def test_revoking_closes_the_gate_again(client, create_test_user, auth_headers):
    admin = await create_test_user(email="admin@ispras.ru", is_superuser=True)
    user = await create_test_user(
        email="user@ispras.ru",
        job_title=UserJobTitle.ANALYST,
        permissions=[Permission.TEST_UPLOAD],
    )
    upload = {"files": {"file": ("case.zip", b"not a zip", "application/zip")}}

    revoked = await client.delete(GRANT.format(user_id=user.id), headers=auth_headers(admin))
    after = await client.post("/tests/upload", headers=auth_headers(user), **upload)

    assert revoked.status_code == status.HTTP_204_NO_CONTENT
    assert after.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio(loop_scope="session")
async def test_granting_twice_is_idempotent(client, create_test_user, auth_headers):
    admin = await create_test_user(email="admin@ispras.ru", is_superuser=True)
    user = await create_test_user(email="user@ispras.ru")

    first = await client.post(GRANT.format(user_id=user.id), headers=auth_headers(admin))
    second = await client.post(GRANT.format(user_id=user.id), headers=auth_headers(admin))
    listed = await client.get(f"/users/{user.id}/permissions", headers=auth_headers(admin))

    assert first.status_code == second.status_code == status.HTTP_204_NO_CONTENT
    assert len(listed.json()) == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_revoking_what_was_never_granted_is_idempotent(
    client, create_test_user, auth_headers
):
    admin = await create_test_user(email="admin@ispras.ru", is_superuser=True)
    user = await create_test_user(email="user@ispras.ru")

    response = await client.delete(GRANT.format(user_id=user.id), headers=auth_headers(admin))

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio(loop_scope="session")
async def test_an_unknown_permission_name_is_rejected(client, create_test_user, auth_headers):
    admin = await create_test_user(is_superuser=True)

    response = await client.post(
        f"/users/{admin.id}/permissions/test:teleport", headers=auth_headers(admin)
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio(loop_scope="session")
async def test_an_unknown_user_is_reported(client, create_test_user, auth_headers):
    admin = await create_test_user(is_superuser=True)
    missing = "00000000-0000-0000-0000-000000000000"

    response = await client.post(GRANT.format(user_id=missing), headers=auth_headers(admin))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("method", ["get", "post", "delete"])
async def test_a_regular_user_cannot_manage_permissions(
    client, create_test_user, auth_headers, method
):
    user = await create_test_user(job_title=UserJobTitle.MANAGER)
    path = (
        f"/users/{user.id}/permissions"
        if method == "get"
        else GRANT.format(user_id=user.id)
    )

    response = await client.request(method, path, headers=auth_headers(user))

    assert response.status_code == status.HTTP_403_FORBIDDEN
