from datetime import UTC, datetime

import pytest

from app.core.config import get_settings
from app.memory_allocator.schemas import UploaderDomain, UploaderResponse
from app.users.schemas import UserDomain, UserResponse
from tests.factories import make_user

settings = get_settings()

SCHEMAS = [UserDomain, UserResponse, UploaderDomain, UploaderResponse]


@pytest.mark.parametrize("schema", SCHEMAS)
def test_no_avatar_gives_null(schema):
    model = schema.model_validate(make_user(avatar_key=None, avatar_updated_at=None))
    assert model.avatar_url is None


@pytest.mark.parametrize("schema", SCHEMAS)
def test_url_is_built_from_the_id_alone(schema):
    updated_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    user = make_user(avatar_key="avatars/whatever.webp", avatar_updated_at=updated_at)

    url = schema.model_validate(user).avatar_url

    assert url == (
        f"{settings.API_PREFIX}/users/{user.id}/avatar?v={int(updated_at.timestamp() * 1_000_000)}"
    )


@pytest.mark.parametrize("schema", SCHEMAS)
def test_version_changes_when_the_picture_does(schema):
    user = make_user(
        avatar_key="avatars/x.webp", avatar_updated_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    before = schema.model_validate(user).avatar_url

    user.avatar_updated_at = datetime(2026, 6, 1, tzinfo=UTC)
    after = schema.model_validate(user).avatar_url

    assert before != after


@pytest.mark.parametrize("schema", SCHEMAS)
def test_source_columns_never_reach_the_client(schema):
    user = make_user(avatar_key="avatars/x.webp", avatar_updated_at=datetime.now(UTC))
    dumped = schema.model_validate(user).model_dump()

    assert "avatar_key" not in dumped
    assert "avatar_updated_at" not in dumped


@pytest.mark.parametrize("schema", SCHEMAS)
def test_key_is_present_even_when_empty(schema):
    dumped = schema.model_validate(make_user(avatar_key=None)).model_dump()

    assert "avatar_url" in dumped
