import uuid

import pytest
from fastapi import status

from app.users.enums import UserJobTitle
from tests.conftest import assert_error_response
from tests.factories import DEFAULT_PASSWORD

BROKEN_ZIP = {"file": ("case.zip", b"not a zip", "application/zip")}
MISSING_USER = uuid.UUID("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio(loop_scope="session")
async def test_registration_does_not_grant_the_requested_role(client):
    response = await client.post("/auth/register", json={
        "email": "applicant@ispras.ru",
        "password": DEFAULT_PASSWORD,
        "first_name": "Nikita",
        "last_name": "Lebedev",
        "job_title": UserJobTitle.DEVELOPER,
    })
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["job_title"] == UserJobTitle.OTHER
    assert body["requested_job_title"] == UserJobTitle.DEVELOPER


@pytest.mark.asyncio(loop_scope="session")
async def test_requested_role_gives_no_access(client, create_test_user, auth_headers):
    applicant = await create_test_user(
        email="applicant@ispras.ru", job_title=UserJobTitle.OTHER
    )
    headers = auth_headers(applicant)

    await client.post(
        "/users/me/role-request",
        headers=headers,
        json={"job_title": UserJobTitle.DEVELOPER},
    )
    response = await client.post("/tests/upload", headers=headers, files=BROKEN_ZIP)

    assert_error_response(response, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
async def test_approved_role_works_without_relogin(client, create_test_user, auth_headers):
    applicant = await create_test_user(
        email="applicant@ispras.ru", job_title=UserJobTitle.OTHER
    )
    moderator = await create_test_user(email="moderator@ispras.ru", is_superuser=True)
    headers = auth_headers(applicant)

    await client.post(
        "/users/me/role-request",
        headers=headers,
        json={"job_title": UserJobTitle.DEVELOPER},
    )
    approval = await client.post(
        f"/users/{applicant.id}/role-request/approve",
        headers=auth_headers(moderator),
        json={"expected_job_title": UserJobTitle.DEVELOPER},
    )
    assert approval.status_code == status.HTTP_200_OK
    assert approval.json()["job_title"] == UserJobTitle.DEVELOPER
    assert approval.json()["requested_job_title"] is None

    response = await client.post("/tests/upload", headers=headers, files=BROKEN_ZIP)

    assert response.status_code != status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio(loop_scope="session")
async def test_approve_rejects_stale_expectation(client, create_test_user, auth_headers):
    applicant = await create_test_user(
        email="applicant@ispras.ru", job_title=UserJobTitle.OTHER
    )
    moderator = await create_test_user(email="moderator@ispras.ru", is_superuser=True)
    headers = auth_headers(applicant)

    await client.post(
        "/users/me/role-request", headers=headers,
        json={"job_title": UserJobTitle.DEVELOPER},
    )
    await client.post(
        "/users/me/role-request", headers=headers,
        json={"job_title": UserJobTitle.MANAGER},
    )
    response = await client.post(
        f"/users/{applicant.id}/role-request/approve",
        headers=auth_headers(moderator),
        json={"expected_job_title": UserJobTitle.DEVELOPER},
    )

    assert_error_response(response, status.HTTP_409_CONFLICT)
    stayed = await client.get(f"/users/{applicant.id}", headers=headers)
    assert stayed.json()["job_title"] == UserJobTitle.OTHER
    assert stayed.json()["requested_job_title"] == UserJobTitle.MANAGER


@pytest.mark.asyncio(loop_scope="session")
async def test_approve_without_open_request(client, create_test_user, auth_headers):
    applicant = await create_test_user(email="applicant@ispras.ru")
    moderator = await create_test_user(email="moderator@ispras.ru", is_superuser=True)

    response = await client.post(
        f"/users/{applicant.id}/role-request/approve",
        headers=auth_headers(moderator),
        json={"expected_job_title": UserJobTitle.MANAGER},
    )

    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
async def test_reject_keeps_the_current_role(client, create_test_user, auth_headers):
    applicant = await create_test_user(email="applicant@ispras.ru")
    moderator = await create_test_user(email="moderator@ispras.ru", is_superuser=True)
    headers = auth_headers(applicant)

    await client.post(
        "/users/me/role-request", headers=headers,
        json={"job_title": UserJobTitle.MANAGER},
    )
    response = await client.post(
        f"/users/{applicant.id}/role-request/reject", headers=auth_headers(moderator)
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["job_title"] == UserJobTitle.DEVELOPER
    assert response.json()["requested_job_title"] is None


@pytest.mark.asyncio(loop_scope="session")
async def test_direct_assignment_drops_the_open_request(
    client, create_test_user, auth_headers
):
    applicant = await create_test_user(email="applicant@ispras.ru")
    moderator = await create_test_user(email="moderator@ispras.ru", is_superuser=True)
    headers = auth_headers(applicant)

    await client.post(
        "/users/me/role-request", headers=headers,
        json={"job_title": UserJobTitle.MANAGER},
    )
    response = await client.put(
        f"/users/{applicant.id}/role",
        headers=auth_headers(moderator),
        json={"job_title": UserJobTitle.ANALYST},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["job_title"] == UserJobTitle.ANALYST
    assert response.json()["requested_job_title"] is None


@pytest.mark.asyncio(loop_scope="session")
async def test_demotion_takes_effect_immediately(client, create_test_user, auth_headers):
    applicant = await create_test_user(
        email="applicant@ispras.ru", job_title=UserJobTitle.DEVELOPER
    )
    moderator = await create_test_user(email="moderator@ispras.ru", is_superuser=True)
    headers = auth_headers(applicant)

    allowed = await client.post("/tests/upload", headers=headers, files=BROKEN_ZIP)
    assert allowed.status_code != status.HTTP_403_FORBIDDEN

    await client.put(
        f"/users/{applicant.id}/role",
        headers=auth_headers(moderator),
        json={"job_title": UserJobTitle.OTHER},
    )
    denied = await client.post("/tests/upload", headers=headers, files=BROKEN_ZIP)

    assert_error_response(denied, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
async def test_role_requests_show_both_roles(client, create_test_user, auth_headers):
    applicant = await create_test_user(
        email="applicant@ispras.ru", job_title=UserJobTitle.OTHER
    )
    moderator = await create_test_user(email="moderator@ispras.ru", is_superuser=True)

    await client.post(
        "/users/me/role-request",
        headers=auth_headers(applicant),
        json={"job_title": UserJobTitle.MANAGER},
    )
    response = await client.get("/users/role-requests", headers=auth_headers(moderator))

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(applicant.id)
    assert body[0]["job_title"] == UserJobTitle.OTHER
    assert body[0]["requested_job_title"] == UserJobTitle.MANAGER


@pytest.mark.asyncio(loop_scope="session")
async def test_role_request_for_the_current_role(client, create_test_user, auth_headers):
    applicant = await create_test_user(email="applicant@ispras.ru")

    response = await client.post(
        "/users/me/role-request",
        headers=auth_headers(applicant),
        json={"job_title": UserJobTitle.DEVELOPER},
    )

    assert_error_response(response, status.HTTP_400_BAD_REQUEST)


@pytest.mark.asyncio(loop_scope="session")
async def test_profile_update_cannot_change_the_role(client, create_test_user, auth_headers):
    applicant = await create_test_user(email="applicant@ispras.ru")

    response = await client.patch(
        f"/users/{applicant.id}",
        headers=auth_headers(applicant),
        json={"job_title": UserJobTitle.MANAGER},
    )

    assert_error_response(response, status.HTTP_422_UNPROCESSABLE_CONTENT)


@pytest.mark.asyncio(loop_scope="session")
async def test_moderation_routes_reject_an_ordinary_user(
    client, create_test_user, auth_headers
):
    ordinary = await create_test_user(email="ordinary@ispras.ru")
    headers = auth_headers(ordinary)

    for response in [
        await client.get("/users/role-requests", headers=headers),
        await client.post(
            f"/users/{MISSING_USER}/role-request/approve",
            headers=headers,
            json={"expected_job_title": UserJobTitle.MANAGER},
        ),
        await client.post(
            f"/users/{MISSING_USER}/role-request/reject", headers=headers
        ),
        await client.put(
            f"/users/{MISSING_USER}/role",
            headers=headers,
            json={"job_title": UserJobTitle.MANAGER},
        ),
    ]:
        assert_error_response(response, status.HTTP_403_FORBIDDEN)
