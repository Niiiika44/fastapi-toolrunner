import logging
import uuid
from datetime import UTC, datetime

import pytest

from app.auth.enums import Permission
from app.users.exceptions import UserNotFoundError
from app.users.services import UserService
from tests.factories import make_user


@pytest.mark.asyncio
async def test_grant_adds_the_permission_and_commits(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user

    await UserService(mock_uow).grant_permission(user.id, Permission.TEST_UPLOAD)

    assert [grant.permission for grant in user.permissions] == [Permission.TEST_UPLOAD]
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_granting_an_existing_permission_is_a_silent_no_op(mock_uow, caplog):
    user = make_user(permissions=[Permission.TEST_UPLOAD])
    mock_uow.users.find_by_id.return_value = user

    with caplog.at_level(logging.DEBUG):
        await UserService(mock_uow).grant_permission(user.id, Permission.TEST_UPLOAD)

    assert len(user.permissions) == 1
    mock_uow.commit.assert_not_awaited()
    messages = [record.getMessage() for record in caplog.records]
    assert "user.permission_already_granted" in messages
    assert "user.permission_granted" not in messages


@pytest.mark.asyncio
async def test_revoke_removes_the_permission_and_commits(mock_uow):
    user = make_user(permissions=[Permission.TEST_UPLOAD, Permission.TAG_MANAGE])
    mock_uow.users.find_by_id.return_value = user

    await UserService(mock_uow).revoke_permission(user.id, Permission.TEST_UPLOAD)

    assert [grant.permission for grant in user.permissions] == [Permission.TAG_MANAGE]
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoking_a_permission_the_user_lacks_is_a_no_op(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user

    await UserService(mock_uow).revoke_permission(user.id, Permission.TEST_UPLOAD)

    assert user.permissions == []
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_returns_the_grants(mock_uow):
    user = make_user(permissions=[Permission.TEST_UPLOAD])
    user.permissions[0].granted_at = datetime.now(UTC)
    mock_uow.users.find_by_id.return_value = user

    grants = await UserService(mock_uow).list_permissions(user.id)

    assert [grant.permission for grant in grants] == [Permission.TEST_UPLOAD]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["list_permissions", "grant_permission", "revoke_permission"])
async def test_unknown_user_is_reported(mock_uow, method):
    mock_uow.users.find_by_id.return_value = None
    service = UserService(mock_uow)
    args = () if method == "list_permissions" else (Permission.TEST_UPLOAD,)

    with pytest.raises(UserNotFoundError):
        await getattr(service, method)(uuid.uuid4(), *args)


@pytest.mark.asyncio
async def test_set_superuser_promotes_and_commits(mock_uow):
    user = make_user(is_superuser=False)
    mock_uow.users.find_by_email.return_value = user

    promoted = await UserService(mock_uow).set_superuser(user.email)

    assert promoted.is_superuser is True
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_superuser_can_demote(mock_uow):
    user = make_user(is_superuser=True)
    mock_uow.users.find_by_email.return_value = user

    demoted = await UserService(mock_uow).set_superuser(user.email, is_superuser=False)

    assert demoted.is_superuser is False


@pytest.mark.asyncio
async def test_set_superuser_reports_an_unknown_account(mock_uow):
    mock_uow.users.find_by_email.return_value = None

    with pytest.raises(UserNotFoundError):
        await UserService(mock_uow).set_superuser("nobody@ispras.ru")
