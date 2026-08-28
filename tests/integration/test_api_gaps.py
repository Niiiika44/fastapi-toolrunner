import uuid

import pytest
from fastapi import status

from app.auth.enums import Permission
from app.auth.permissions import ROLE_PERMISSIONS
from app.memory_allocator.enums import ArtifactKind, TestStatus
from app.memory_allocator.models import Tag, TestArtifact
from app.users.enums import UserJobTitle
from tests.conftest import assert_error_response
from tests.factories import make_platform, make_test


@pytest.mark.asyncio(loop_scope="session")
async def test_me_reports_the_role_baseline(client, create_test_user, auth_headers):
    user = await create_test_user(email="analyst@ispras.ru", job_title=UserJobTitle.ANALYST)

    response = await client.get("/users/me", headers=auth_headers(user))

    assert set(response.json()["permissions"]) == {
        str(p) for p in ROLE_PERMISSIONS[UserJobTitle.ANALYST]
    }


@pytest.mark.asyncio(loop_scope="session")
async def test_me_includes_individual_grants(client, create_test_user, auth_headers):
    user = await create_test_user(
        email="granted@ispras.ru",
        job_title=UserJobTitle.OTHER,
        permissions=[Permission.TEST_UPLOAD],
    )

    permissions = (await client.get("/users/me", headers=auth_headers(user))).json()["permissions"]

    assert str(Permission.TEST_UPLOAD) in permissions
    assert str(Permission.TEST_READ) in permissions, "the baseline is still there"


@pytest.mark.asyncio(loop_scope="session")
async def test_me_gives_a_superuser_everything(client, create_test_user, auth_headers):
    user = await create_test_user(email="root@ispras.ru", is_superuser=True)

    permissions = (await client.get("/users/me", headers=auth_headers(user))).json()["permissions"]

    assert set(permissions) == {str(p) for p in Permission}


@pytest.mark.asyncio(loop_scope="session")
async def test_reported_permissions_match_what_the_gates_allow(
    client, create_test_user, auth_headers
):
    user = await create_test_user(email="matching@ispras.ru", job_title=UserJobTitle.MANAGER)
    headers = auth_headers(user)
    permissions = (await client.get("/users/me", headers=headers)).json()["permissions"]

    listing = await client.get("/tests", headers=headers)
    upload = await client.post(
        "/tests/upload", files={"file": ("t.zip", b"PK\x03\x04", "application/zip")},
        headers=headers,
    )

    assert (str(Permission.TEST_READ) in permissions) is (listing.status_code == status.HTTP_200_OK)
    assert str(Permission.TEST_UPLOAD) not in permissions
    assert upload.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio(loop_scope="session")
async def test_withdraw_own_role_request(client, create_test_user, auth_headers):
    user = await create_test_user(email="undecided@ispras.ru", job_title=UserJobTitle.OTHER)
    headers = auth_headers(user)
    await client.post("/users/me/role-request", json={"job_title": "developer"}, headers=headers)
    assert (await client.get("/users/me", headers=headers)).json()["requested_job_title"]

    withdrawn = await client.delete("/users/me/role-request", headers=headers)

    assert withdrawn.status_code == status.HTTP_204_NO_CONTENT
    me = (await client.get("/users/me", headers=headers)).json()
    assert me["requested_job_title"] is None
    assert me["job_title"] == UserJobTitle.OTHER, "withdrawing must not touch the role held"


@pytest.mark.asyncio(loop_scope="session")
async def test_withdrawing_twice_is_fine(client, create_test_user, auth_headers):
    user = await create_test_user(email="twice@ispras.ru", job_title=UserJobTitle.OTHER)
    headers = auth_headers(user)

    first = await client.delete("/users/me/role-request", headers=headers)
    second = await client.delete("/users/me/role-request", headers=headers)

    assert first.status_code == second.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio(loop_scope="session")
async def test_withdrawing_needs_a_token(client):
    assert_error_response(
        await client.delete("/users/me/role-request"), status.HTTP_401_UNAUTHORIZED
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_withdrawn_request_leaves_the_moderation_queue(
    client, create_test_user, auth_headers
):
    user = await create_test_user(email="queued@ispras.ru", job_title=UserJobTitle.OTHER)
    moderator = await create_test_user(
        email="mod@ispras.ru", permissions=[Permission.USER_UPDATE_ANY]
    )
    headers = auth_headers(user)
    await client.post("/users/me/role-request", json={"job_title": "tester"}, headers=headers)

    await client.delete("/users/me/role-request", headers=headers)

    queue = await client.get("/users/role-requests", headers=auth_headers(moderator))
    assert user.email not in {item["email"] for item in queue.json()}


@pytest.mark.asyncio(loop_scope="session")
async def test_test_case_carries_its_tags(client, db_session, create_test_user, auth_headers):
    user = await create_test_user(email="tagger@ispras.ru")
    headers = auth_headers(user)
    test = make_test(status=TestStatus.PARSED, uploaded_by=user)
    tag = Tag(name="regression-gap")
    db_session.add_all([test, tag])
    await db_session.commit()

    assert (await client.get(f"/tests/{test.id}", headers=headers)).json()["tags"] == []

    await client.post(f"/tests/{test.id}/tags/{tag.id}", headers=headers)

    detail = (await client.get(f"/tests/{test.id}", headers=headers)).json()
    assert [t["name"] for t in detail["tags"]] == ["regression-gap"]


@pytest.mark.asyncio(loop_scope="session")
async def test_tags_survive_the_listing(client, db_session, create_test_user, auth_headers):
    user = await create_test_user(email="listtagger@ispras.ru")
    headers = auth_headers(user)
    test = make_test(status=TestStatus.PARSED, uploaded_by=user)
    tag = Tag(name="listed-gap")
    db_session.add_all([test, tag])
    await db_session.commit()
    await client.post(f"/tests/{test.id}/tags/{tag.id}", headers=headers)

    listing = await client.get("/tests", headers=headers)

    listed = next(item for item in listing.json()["tests"] if item["id"] == test.id)
    assert [t["name"] for t in listed["tags"]] == ["listed-gap"]


@pytest.mark.asyncio(loop_scope="session")
async def test_detaching_removes_the_tag_from_the_payload(
    client, db_session, create_test_user, auth_headers
):
    user = await create_test_user(email="detacher@ispras.ru")
    headers = auth_headers(user)
    test = make_test(status=TestStatus.PARSED, uploaded_by=user)
    tag = Tag(name="detached-gap")
    db_session.add_all([test, tag])
    await db_session.commit()
    await client.post(f"/tests/{test.id}/tags/{tag.id}", headers=headers)

    await client.delete(f"/tests/{test.id}/tags/{tag.id}", headers=headers)

    assert (await client.get(f"/tests/{test.id}", headers=headers)).json()["tags"] == []


@pytest.mark.asyncio(loop_scope="session")
async def test_artifacts_are_listed_with_ids(client, db_session, create_test_user, auth_headers):
    user = await create_test_user(email="artifacts@ispras.ru")
    test = make_test(status=TestStatus.PARSED, uploaded_by=user)
    memin = TestArtifact(
        kind=ArtifactKind.CONFIG, filename="memin.yaml",
        storage_key="artifacts/9/memin.yaml", test=test,
    )
    log = TestArtifact(
        kind=ArtifactKind.LOG, filename="memin.log",
        storage_key="artifacts/9/memin.log", test=test,
    )
    db_session.add_all([test, memin, log])
    await db_session.commit()

    response = await client.get(f"/tests/{test.id}/artifacts", headers=auth_headers(user))

    assert response.status_code == status.HTTP_200_OK
    listed = response.json()
    assert {item["filename"] for item in listed} == {"memin.yaml", "memin.log"}
    assert {item["kind"] for item in listed} == {"config", "log"}
    assert all(isinstance(item["id"], int) for item in listed)


@pytest.mark.asyncio(loop_scope="session")
async def test_artifact_listing_hides_the_storage_key(
    client, db_session, create_test_user, auth_headers
):
    user = await create_test_user(email="nokeys@ispras.ru")
    test = make_test(status=TestStatus.PARSED, uploaded_by=user)
    db_session.add_all([
        test,
        TestArtifact(
            kind=ArtifactKind.CONFIG, filename="memin.yaml",
            storage_key="artifacts/10/memin.yaml", test=test,
        ),
    ])
    await db_session.commit()

    listed = (
        await client.get(f"/tests/{test.id}/artifacts", headers=auth_headers(user))
    ).json()

    assert "storage_key" not in listed[0]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_listed_id_actually_downloads(
    client, db_session, create_test_user, auth_headers, tmp_path
):
    from app.core.storage import LocalStorage

    user = await create_test_user(email="roundtrip@ispras.ru")
    headers = auth_headers(user)
    test = make_test(status=TestStatus.PARSED, uploaded_by=user)
    db_session.add_all([
        test,
        TestArtifact(
            kind=ArtifactKind.CONFIG, filename="memin.yaml",
            storage_key="artifacts/11/memin.yaml", test=test,
        ),
    ])
    await db_session.commit()
    await LocalStorage(tmp_path).save("artifacts/11/memin.yaml", b"memin-content")

    listed = (await client.get(f"/tests/{test.id}/artifacts", headers=headers)).json()
    downloaded = await client.get(
        f"/tests/{test.id}/artifacts/{listed[0]['id']}/download", headers=headers
    )

    assert downloaded.content == b"memin-content"


@pytest.mark.asyncio(loop_scope="session")
async def test_artifacts_of_a_missing_test(client, create_test_user, auth_headers):
    user = await create_test_user(email="missingtest@ispras.ru")

    assert_error_response(
        await client.get("/tests/987654/artifacts", headers=auth_headers(user)),
        status.HTTP_404_NOT_FOUND,
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_artifact_listing_needs_the_export_permission(
    client, db_session, create_test_user, auth_headers
):
    owner = await create_test_user(email="owner-art@ispras.ru")
    reader = await create_test_user(email="reader-art@ispras.ru", job_title=UserJobTitle.OTHER)
    test = make_test(status=TestStatus.PARSED, uploaded_by=owner)
    db_session.add(test)
    await db_session.commit()

    response = await client.get(f"/tests/{test.id}/artifacts", headers=auth_headers(reader))

    assert_error_response(response, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
async def test_artifacts_of_an_unparsed_test_are_empty(
    client, db_session, create_test_user, auth_headers
):
    user = await create_test_user(email="pendingart@ispras.ru")
    test = make_test(status=TestStatus.PENDING, uploaded_by=user)
    db_session.add(test)
    await db_session.commit()

    response = await client.get(f"/tests/{test.id}/artifacts", headers=auth_headers(user))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.asyncio(loop_scope="session")
async def test_artifacts_of_another_test_are_not_mixed_in(
    client, db_session, create_test_user, auth_headers
):
    user = await create_test_user(email="separate@ispras.ru")
    platform = make_platform()
    mine = make_test(
        id=None, status=TestStatus.PARSED, uploaded_by=user, name="mine", platform=platform
    )
    other = make_test(
        id=None, status=TestStatus.PARSED, uploaded_by=user, name="other", platform=platform
    )
    db_session.add_all([
        mine, other,
        TestArtifact(kind=ArtifactKind.LOG, filename="mine.log",
                     storage_key="artifacts/mine.log", test=mine),
        TestArtifact(kind=ArtifactKind.LOG, filename="other.log",
                     storage_key="artifacts/other.log", test=other),
    ])
    await db_session.commit()

    listed = (
        await client.get(f"/tests/{mine.id}/artifacts", headers=auth_headers(user))
    ).json()

    assert [item["filename"] for item in listed] == ["mine.log"]


@pytest.mark.asyncio(loop_scope="session")
async def test_download_rejects_an_artifact_from_another_test(
    client, db_session, create_test_user, auth_headers
):
    user = await create_test_user(email="crosstest@ispras.ru")
    platform = make_platform()
    mine = make_test(
        id=None, status=TestStatus.PARSED, uploaded_by=user, name="a", platform=platform
    )
    other = make_test(
        id=None, status=TestStatus.PARSED, uploaded_by=user, name="b", platform=platform
    )
    artifact = TestArtifact(
        kind=ArtifactKind.LOG, filename="other.log",
        storage_key="artifacts/other.log", test=other,
    )
    db_session.add_all([mine, other, artifact])
    await db_session.commit()

    response = await client.get(
        f"/tests/{mine.id}/artifacts/{artifact.id}/download", headers=auth_headers(user)
    )

    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
async def test_unknown_uuid_still_answers_the_same_everywhere(client, create_test_user):
    stranger = uuid.uuid4()
    assert (await client.get(f"/users/{stranger}/avatar")).status_code == 404
