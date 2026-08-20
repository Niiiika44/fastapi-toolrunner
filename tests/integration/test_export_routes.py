import io
import zipfile

import pytest
from fastapi import status

from app.core.storage import LocalStorage
from app.memory_allocator.enums import ArtifactKind, TestStatus
from app.memory_allocator.models import TestArtifact
from tests.conftest import assert_error_response
from tests.factories import make_platform, make_test


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_export_success(
    client,
    db_session,
    create_test_user,
    auth_headers,
    tmp_path,
):
    user = await create_test_user()
    test = make_test(status=TestStatus.PARSED, uploaded_by=user, name="mips")
    memin = TestArtifact(
        kind=ArtifactKind.CONFIG, filename="memin.yaml",
        storage_key="artifacts/1/memin.yaml", test=test,
    )
    log = TestArtifact(
        kind=ArtifactKind.LOG, filename="memin.log",
        storage_key="artifacts/1/memin.log", test=test,
    )
    db_session.add_all([test, memin, log])
    await db_session.commit()

    storage = LocalStorage(tmp_path)
    await storage.save("artifacts/1/memin.yaml", b"memin-content")
    await storage.save("artifacts/1/memin.log", b"log-content")

    response = await client.get(f"/tests/{test.id}/export", headers=auth_headers(user))

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/zip"
    assert 'filename="mips.zip"' in response.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        assert set(zf.namelist()) == {"memin.yaml", "memin.log"}
        assert zf.read("memin.yaml") == b"memin-content"


@pytest.mark.asyncio(loop_scope="session")
async def test_export_not_parsed(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    test = make_test(status=TestStatus.PENDING, uploaded_by=user)
    db_session.add(test)
    await db_session.commit()

    response = await client.get(f"/tests/{test.id}/export", headers=auth_headers(user))

    assert_error_response(response, status.HTTP_409_CONFLICT)


@pytest.mark.asyncio(loop_scope="session")
async def test_export_nonexisting_test(client, create_test_user, auth_headers):
    user = await create_test_user()

    response = await client.get("/tests/123/export", headers=auth_headers(user))

    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
async def test_export_no_user(client):
    response = await client.get("/tests/1/export")

    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_download_artifact_streams_from_local_storage(
    client,
    db_session,
    create_test_user,
    auth_headers,
    tmp_path,
):
    user = await create_test_user()
    test = make_test(status=TestStatus.PARSED, uploaded_by=user, name="mips")
    memin = TestArtifact(
        kind=ArtifactKind.CONFIG, filename="memin.yaml",
        storage_key="artifacts/1/memin.yaml", test=test,
    )
    db_session.add_all([test, memin])
    await db_session.commit()
    await LocalStorage(tmp_path).save("artifacts/1/memin.yaml", b"memin-content")

    response = await client.get(
        f"/tests/{test.id}/artifacts/{memin.id}/download", headers=auth_headers(user)
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/octet-stream"
    assert 'filename="memin.yaml"' in response.headers["content-disposition"]
    assert response.content == b"memin-content"


@pytest.mark.asyncio(loop_scope="session")
async def test_download_artifact_redirects_when_storage_signs_links(
    client,
    db_session,
    create_test_user,
    auth_headers,
    presigning_storage,
):
    user = await create_test_user()
    test = make_test(status=TestStatus.PARSED, uploaded_by=user, name="mips")
    memin = TestArtifact(
        kind=ArtifactKind.CONFIG, filename="memin.yaml",
        storage_key="artifacts/1/memin.yaml", test=test,
    )
    db_session.add_all([test, memin])
    await db_session.commit()
    await presigning_storage.save("artifacts/1/memin.yaml", b"memin-content")

    response = await client.get(
        f"/tests/{test.id}/artifacts/{memin.id}/download",
        headers=auth_headers(user),
        follow_redirects=False,
    )

    assert response.status_code == status.HTTP_302_FOUND
    assert response.headers["location"] == presigning_storage.url
    assert not response.content


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_download_artifact_of_another_test_is_not_found(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    platform = make_platform(id=None)
    own_test = make_test(
        id=None, status=TestStatus.PARSED, uploaded_by=user, platform=platform, name="mine"
    )
    other_test = make_test(
        id=None, status=TestStatus.PARSED, uploaded_by=user, platform=platform, name="other"
    )
    stranger = TestArtifact(
        kind=ArtifactKind.CONFIG, filename="memin.yaml",
        storage_key="artifacts/2/memin.yaml", test=other_test,
    )
    db_session.add_all([own_test, other_test, stranger])
    await db_session.commit()

    response = await client.get(
        f"/tests/{own_test.id}/artifacts/{stranger.id}/download", headers=auth_headers(user)
    )

    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_download_missing_artifact_is_not_found(
    client, db_session, create_test_user, auth_headers
):
    user = await create_test_user()
    test = make_test(status=TestStatus.PARSED, uploaded_by=user, name="mips")
    db_session.add(test)
    await db_session.commit()

    response = await client.get(
        f"/tests/{test.id}/artifacts/999/download", headers=auth_headers(user)
    )

    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
async def test_download_artifact_no_user(client):
    response = await client.get("/tests/1/artifacts/1/download")

    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
