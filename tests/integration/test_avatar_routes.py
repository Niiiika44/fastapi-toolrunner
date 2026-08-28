import io

import pytest
from fastapi import status
from PIL import Image

from app.auth.enums import Permission
from app.core.config import get_settings
from app.users.enums import UserJobTitle
from tests.conftest import assert_error_response
from tests.factories import make_image_bytes

settings = get_settings()


def png(**kwargs) -> dict:
    return {"file": ("photo.png", make_image_bytes(**kwargs), "image/png")}


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_upload_then_read_then_delete(client, create_test_user, auth_headers):
    user = await create_test_user(email="owner@ispras.ru")
    headers = auth_headers(user)

    assert (await client.get("/users/me", headers=headers)).json()["avatar_url"] is None

    uploaded = await client.post(f"/users/{user.id}/avatar", files=png(), headers=headers)
    assert uploaded.status_code == status.HTTP_200_OK
    url = uploaded.json()["avatar_url"]
    assert url.startswith(f"{settings.API_PREFIX}/users/{user.id}/avatar?v=")

    me = await client.get("/users/me", headers=headers)
    assert me.json()["avatar_url"] == url

    picture = await client.get(f"/users/{user.id}/avatar")
    assert picture.status_code == status.HTTP_200_OK
    assert Image.open(io.BytesIO(picture.content)).format == "WEBP"

    removed = await client.delete(f"/users/{user.id}/avatar", headers=headers)
    assert removed.status_code == status.HTTP_204_NO_CONTENT

    assert (await client.get("/users/me", headers=headers)).json()["avatar_url"] is None
    assert_error_response(
        await client.get(f"/users/{user.id}/avatar"), status.HTTP_404_NOT_FOUND
    )


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_picture_needs_no_token(client, create_test_user, auth_headers):
    user = await create_test_user(email="public@ispras.ru")
    await client.post(f"/users/{user.id}/avatar", files=png(), headers=auth_headers(user))

    response = await client.get(f"/users/{user.id}/avatar")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["cache-control"] == (
        f"public, max-age={settings.AVATAR_CACHE_SECONDS}"
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_cache_never_outlives_the_signature():
    assert settings.AVATAR_CACHE_SECONDS < settings.S3_PRESIGN_TTL_SECONDS


@pytest.mark.asyncio(loop_scope="session")
async def test_link_backend_redirects(client, create_test_user, auth_headers, presigning_storage):
    user = await create_test_user(email="signed@ispras.ru")
    await client.post(f"/users/{user.id}/avatar", files=png(), headers=auth_headers(user))

    response = await client.get(f"/users/{user.id}/avatar", follow_redirects=False)

    assert response.status_code == status.HTTP_302_FOUND
    assert response.headers["location"] == presigning_storage.url


@pytest.mark.asyncio(loop_scope="session")
async def test_missing_user_and_missing_picture_are_indistinguishable(
    client, create_test_user
):
    import uuid

    user = await create_test_user(email="nopicture@ispras.ru")

    without_picture = await client.get(f"/users/{user.id}/avatar")
    without_user = await client.get(f"/users/{uuid.uuid4()}/avatar")

    assert without_picture.status_code == without_user.status_code == status.HTTP_404_NOT_FOUND
    assert without_picture.json() == without_user.json()


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_replacing_changes_the_url(client, create_test_user, auth_headers):
    user = await create_test_user(email="replacer@ispras.ru")
    headers = auth_headers(user)

    first = await client.post(f"/users/{user.id}/avatar", files=png(), headers=headers)
    second = await client.post(
        f"/users/{user.id}/avatar", files=png(width=300, height=300), headers=headers
    )

    assert second.json()["avatar_url"] != first.json()["avatar_url"]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_upload_rejects_a_file_that_is_not_an_image(client, create_test_user, auth_headers):
    user = await create_test_user(email="pdf@ispras.ru")

    response = await client.post(
        f"/users/{user.id}/avatar",
        files={"file": ("cv.pdf", b"%PDF-1.7\n%\xe2\xe3\xcf\xd3", "image/png")},
        headers=auth_headers(user),
    )

    assert_error_response(response, status.HTTP_400_BAD_REQUEST)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_upload_rejects_an_oversized_image(client, create_test_user, auth_headers):
    user = await create_test_user(email="huge@ispras.ru")
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (settings.AVATAR_MAX_BYTES + 1)

    response = await client.post(
        f"/users/{user.id}/avatar",
        files={"file": ("huge.png", oversized, "image/png")},
        headers=auth_headers(user),
    )

    assert_error_response(response, status.HTTP_413_CONTENT_TOO_LARGE)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_upload_needs_a_token(client, create_test_user):
    user = await create_test_user(email="anon@ispras.ru")

    response = await client.post(f"/users/{user.id}/avatar", files=png())

    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_a_stranger_cannot_change_someone_else_picture(
    client, create_test_user, auth_headers
):
    owner = await create_test_user(email="victim@ispras.ru")
    stranger = await create_test_user(email="stranger@ispras.ru", job_title=UserJobTitle.ANALYST)

    upload = await client.post(
        f"/users/{owner.id}/avatar", files=png(), headers=auth_headers(stranger)
    )
    removal = await client.delete(f"/users/{owner.id}/avatar", headers=auth_headers(stranger))

    assert_error_response(upload, status.HTTP_403_FORBIDDEN)
    assert_error_response(removal, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_a_moderator_may_change_someone_else_picture(
    client, create_test_user, auth_headers
):
    owner = await create_test_user(email="managed@ispras.ru")
    moderator = await create_test_user(
        email="moderator@ispras.ru", permissions=[Permission.USER_UPDATE_ANY]
    )

    response = await client.post(
        f"/users/{owner.id}/avatar", files=png(), headers=auth_headers(moderator)
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_delete_is_idempotent(client, create_test_user, auth_headers):
    user = await create_test_user(email="idempotent@ispras.ru")
    headers = auth_headers(user)

    first = await client.delete(f"/users/{user.id}/avatar", headers=headers)
    second = await client.delete(f"/users/{user.id}/avatar", headers=headers)

    assert first.status_code == second.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_deleting_the_account_takes_the_picture_with_it(
    client, create_test_user, auth_headers
):
    user = await create_test_user(email="leaving@ispras.ru")
    headers = auth_headers(user)
    await client.post(f"/users/{user.id}/avatar", files=png(), headers=headers)

    removed = await client.delete(f"/users/{user.id}", headers=headers)

    assert removed.status_code == status.HTTP_204_NO_CONTENT
    assert_error_response(
        await client.get(f"/users/{user.id}/avatar"), status.HTTP_404_NOT_FOUND
    )


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_storage")
async def test_uploader_of_a_test_carries_a_picture(
    client, create_test_user, auth_headers, db_session
):
    from app.memory_allocator.enums import TestStatus
    from tests.factories import make_test

    user = await create_test_user(email="uploader@ispras.ru")
    headers = auth_headers(user)
    test = make_test(status=TestStatus.PARSED, uploaded_by=user)
    db_session.add(test)
    await db_session.commit()

    await client.post(f"/users/{user.id}/avatar", files=png(), headers=headers)
    listed = await client.get("/tests", headers=headers)

    uploader = next(
        item["uploaded_by"] for item in listed.json()["tests"] if item["id"] == test.id
    )
    assert uploader["avatar_url"] is not None
