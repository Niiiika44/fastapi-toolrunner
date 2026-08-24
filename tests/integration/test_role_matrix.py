import pytest
from fastapi import status

from app.users.enums import UserJobTitle

BROKEN_ZIP = {"files": {"file": ("case.zip", b"not a zip", "application/zip")}}
ROLE_EXPECTATIONS = [
    (UserJobTitle.DEVELOPER, "POST", "/tests/upload", True, BROKEN_ZIP),
    (UserJobTitle.DEVELOPER, "POST", "/tags", True, {"json": {"name": "dev"}}),
    (UserJobTitle.DEVELOPER, "GET", "/users", False, {}),
    (UserJobTitle.TESTER, "POST", "/tests/999999/validate", True, {}),
    (UserJobTitle.TESTER, "POST", "/tags", True, {"json": {"name": "qa"}}),
    (UserJobTitle.ANALYST, "POST", "/tests/upload", False, BROKEN_ZIP),
    (UserJobTitle.ANALYST, "POST", "/tags", False, {"json": {"name": "an"}}),
    (UserJobTitle.ANALYST, "GET", "/tests/999999/export", True, {}),
    (UserJobTitle.ANALYST, "POST", "/tests/999999/tags/999999", True, {}),
    (UserJobTitle.MANAGER, "GET", "/users", True, {}),
    (UserJobTitle.MANAGER, "POST", "/tests/999999/validate", False, {}),
    (UserJobTitle.MANAGER, "POST", "/tests/999999/tags/999999", False, {}),
    (UserJobTitle.OTHER, "GET", "/tests", True, {}),
    (UserJobTitle.OTHER, "GET", "/platforms", True, {}),
    (UserJobTitle.OTHER, "GET", "/tests/999999/export", False, {}),
]
IDS = [
    f"{role.value} {method} {path} {'allowed' if allowed else 'denied'}"
    for role, method, path, allowed, _ in ROLE_EXPECTATIONS
]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    ("role", "method", "path", "allowed", "payload"), ROLE_EXPECTATIONS, ids=IDS
)
async def test_role_reaches_only_what_it_should(
    client, create_test_user, auth_headers, role, method, path, allowed, payload
):
    user = await create_test_user(job_title=role)

    response = await client.request(method, path, headers=auth_headers(user), **payload)

    forbidden = response.status_code == status.HTTP_403_FORBIDDEN
    assert forbidden is not allowed
