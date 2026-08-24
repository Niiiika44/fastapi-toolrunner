import pytest
from fastapi import status

from app.auth.enums import Permission
from app.auth.permissions import ROLE_PERMISSIONS
from app.users.enums import UserJobTitle

NARROWEST_ROLE = UserJobTitle.OTHER
BASELINE = frozenset({Permission.TEST_READ, Permission.PLATFORM_READ})
BROKEN_ZIP = {"file": ("case.zip", b"not a zip", "application/zip")}
MISSING_USER = "00000000-0000-0000-0000-000000000000"
ROLE_BODY = {"json": {"job_title": UserJobTitle.DEVELOPER}}
APPROVAL_BODY = {"json": {"expected_job_title": UserJobTitle.DEVELOPER}}
GATED_ROUTES = [
    ("GET", "/tests", Permission.TEST_READ, {}),
    ("GET", "/tests/999999", Permission.TEST_READ, {}),
    ("GET", "/tests/999999/validations", Permission.TEST_READ, {}),
    ("POST", "/tests/upload", Permission.TEST_UPLOAD, {"files": BROKEN_ZIP}),
    ("POST", "/tests/999999/validate", Permission.TEST_VALIDATE, {}),
    ("POST", "/tests/999999/tags/999999", Permission.TEST_TAG, {}),
    ("DELETE", "/tests/999999/tags/999999", Permission.TEST_TAG, {}),
    ("GET", "/tests/999999/export", Permission.TEST_EXPORT, {}),
    ("GET", "/tests/999999/artifacts/999999/download", Permission.TEST_EXPORT, {}),
    ("GET", "/platforms", Permission.PLATFORM_READ, {}),
    ("GET", "/platforms/999999", Permission.PLATFORM_READ, {}),
    ("GET", "/tags", Permission.TEST_READ, {}),
    ("GET", "/tags/999999", Permission.TEST_READ, {}),
    ("POST", "/tags", Permission.TAG_MANAGE, {"json": {"name": "gate"}}),
    ("DELETE", "/tags/999999", Permission.TAG_MANAGE, {}),
    ("GET", "/users", Permission.USER_READ_ANY, {}),
    ("GET", "/users/role-requests", Permission.USER_UPDATE_ANY, {}),
    ("POST", f"/users/{MISSING_USER}/role-request/approve",
     Permission.USER_UPDATE_ANY, APPROVAL_BODY),
    ("POST", f"/users/{MISSING_USER}/role-request/reject", Permission.USER_UPDATE_ANY, {}),
    ("PUT", f"/users/{MISSING_USER}/role", Permission.USER_UPDATE_ANY, ROLE_BODY),
]
DENIABLE_ROUTES = [route for route in GATED_ROUTES if route[2] not in BASELINE]
IDS = [f"{method} {path}" for method, path, _, _ in GATED_ROUTES]
DENIABLE_IDS = [f"{method} {path}" for method, path, _, _ in DENIABLE_ROUTES]


def test_every_role_holds_the_baseline_permissions():
    assert all(BASELINE <= permissions for permissions in ROLE_PERMISSIONS.values())


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    ("method", "path", "permission", "payload"), DENIABLE_ROUTES, ids=DENIABLE_IDS
)
async def test_route_is_denied_without_the_permission(
    client, create_test_user, auth_headers, method, path, permission, payload
):
    everything_else = [name for name in Permission if name is not permission]
    user = await create_test_user(job_title=NARROWEST_ROLE, permissions=everything_else)

    response = await client.request(
        method, path, headers=auth_headers(user), **payload
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(("method", "path", "permission", "payload"), GATED_ROUTES, ids=IDS)
async def test_route_is_reachable_with_the_permission(
    client, create_test_user, auth_headers, method, path, permission, payload
):
    user = await create_test_user(job_title=NARROWEST_ROLE, permissions=[permission])

    response = await client.request(
        method, path, headers=auth_headers(user), **payload
    )

    assert response.status_code != status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio(loop_scope="session")
async def test_superuser_passes_every_gate(client, create_test_user, auth_headers):
    admin = await create_test_user(job_title=NARROWEST_ROLE, is_superuser=True)

    for method, path, _, payload in GATED_ROUTES:
        response = await client.request(
            method, path, headers=auth_headers(admin), **payload
        )
        assert response.status_code != status.HTTP_403_FORBIDDEN, f"{method} {path}"


@pytest.mark.asyncio(loop_scope="session")
async def test_stranger_cannot_update_another_account(client, create_test_user, auth_headers):
    owner = await create_test_user(email="owner@ispras.ru")
    stranger = await create_test_user(email="stranger@ispras.ru")

    response = await client.patch(
        f"/users/{owner.id}", json={"first_name": "Mallory"}, headers=auth_headers(stranger)
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio(loop_scope="session")
async def test_user_update_any_grant_allows_editing_another_account(
    client, create_test_user, auth_headers
):
    owner = await create_test_user(email="owner@ispras.ru")
    editor = await create_test_user(
        email="editor@ispras.ru", permissions=[Permission.USER_UPDATE_ANY]
    )

    response = await client.patch(
        f"/users/{owner.id}", json={"first_name": "Edited"}, headers=auth_headers(editor)
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["first_name"] == "Edited"


@pytest.mark.asyncio(loop_scope="session")
async def test_owner_may_edit_their_own_account_without_any_permission(
    client, create_test_user, auth_headers
):
    owner = await create_test_user(job_title=NARROWEST_ROLE)

    response = await client.patch(
        f"/users/{owner.id}", json={"first_name": "Self"}, headers=auth_headers(owner)
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio(loop_scope="session")
async def test_user_delete_any_grant_allows_deleting_another_account(
    client, create_test_user, auth_headers
):
    victim = await create_test_user(email="victim@ispras.ru")
    remover = await create_test_user(
        email="remover@ispras.ru", permissions=[Permission.USER_DELETE_ANY]
    )

    response = await client.delete(f"/users/{victim.id}", headers=auth_headers(remover))

    assert response.status_code == status.HTTP_204_NO_CONTENT
