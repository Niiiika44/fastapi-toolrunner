import uuid

import pytest
from pydantic import ValidationError

from app.auth.hash_utils import verify_password
from app.users.enums import UserJobTitle
from app.users.exceptions import (
    EmailDomainNotAllowedError,
    InvalidPasswordError,
    RoleAlreadyAssignedError,
    RoleRequestConflictError,
    RoleRequestNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.users.models import User
from app.users.schemas import UserDomain, UserUpdate
from app.users.services import UserService
from tests.factories import DEFAULT_PASSWORD, make_user, make_user_create


def _simulate_db_refresh(user, *args, **kwargs):
    """Mimic DB-assigned fields on refresh."""
    if user.id is None:
        user.id = uuid.uuid4()
    if user.is_superuser is None:
        user.is_superuser = False


@pytest.mark.asyncio
async def test_create_success(mock_uow):
    mock_uow.users.find_by_email.return_value = None
    mock_uow.refresh.side_effect = _simulate_db_refresh
    service = UserService(mock_uow)
    result = await service.create(make_user_create())
    assert isinstance(result, UserDomain)
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_email", [
    "wrong.email@mail.ru",
    "wrong_email@gmail.com",
    "w.r.o.n.g_email@isp.ru",
    "wrong_e.m.a.i.l@ispras.com",
])
async def test_create_invalid_email(mock_uow, invalid_email):
    service = UserService(mock_uow)
    with pytest.raises(EmailDomainNotAllowedError):
        await service.create(make_user_create(email=invalid_email))
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_duplicate(mock_uow):
    mock_uow.users.find_by_email.return_value = User()
    service = UserService(mock_uow)
    with pytest.raises(UserAlreadyExistsError):
        await service.create(make_user_create())
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_password_hashed(mock_uow):
    mock_uow.users.find_by_email.return_value = None
    mock_uow.refresh.side_effect = _simulate_db_refresh
    service = UserService(mock_uow)
    user_data = make_user_create()
    await service.create(user_data)

    added_user = mock_uow.users.add.call_args.args[0]
    assert added_user.password != user_data.password
    assert verify_password("password", added_user.password)


@pytest.mark.asyncio
async def test_create_username(mock_uow):
    mock_uow.users.find_by_email.return_value = None
    mock_uow.refresh.side_effect = _simulate_db_refresh
    service = UserService(mock_uow)
    result = await service.create(make_user_create())
    assert result.username == "test"


@pytest.mark.asyncio
async def test_get_by_id_existing_user(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    result = await service.get_by_id(user.id)
    assert isinstance(result, UserDomain)
    assert result.id == user.id


@pytest.mark.asyncio
async def test_get_by_id_nonexisting_user(mock_uow):
    mock_uow.users.find_by_id.return_value = None
    service = UserService(mock_uow)
    random_uuid = uuid.uuid4()
    with pytest.raises(UserNotFoundError):
        await service.get_by_id(random_uuid)


@pytest.mark.asyncio
async def test_change_password_success(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    result = await service.change_password(
        user.id, DEFAULT_PASSWORD, "new_password"
    )
    assert isinstance(result, UserDomain)
    assert verify_password("new_password", user.password)
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_password_failure(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    with pytest.raises(InvalidPasswordError):
        await service.change_password(
            user.id, "old_password", "new_password"
        )
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_email_success(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    mock_uow.users.find_by_email.return_value = None
    new_email = "new_email@ispras.ru"
    service = UserService(mock_uow)
    result = await service.change_email(
        user.id, new_email, DEFAULT_PASSWORD
    )
    assert isinstance(result, UserDomain)
    assert result.email == new_email
    assert result.username == "new_email"
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_same_email(mock_uow):
    email = "test@ispras.ru"
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    result = await service.change_email(
        user.id, email, DEFAULT_PASSWORD
    )
    assert isinstance(result, UserDomain)
    assert result.email == email
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_email_wrong_password(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    with pytest.raises(InvalidPasswordError):
        await service.change_email(
            user.id, "new_email@ispras.ru", "new_password"
        )
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_email_wrong_domain(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    with pytest.raises(EmailDomainNotAllowedError):
        await service.change_email(
            user.id, "new_email@ispras.com", DEFAULT_PASSWORD
        )
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_email_existing_email(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    mock_uow.users.find_by_email.return_value = User()
    service = UserService(mock_uow)
    with pytest.raises(UserAlreadyExistsError):
        await service.change_email(
            user.id, "new_email@ispras.ru", DEFAULT_PASSWORD
        )
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_correct_field(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    user_update = UserUpdate(first_name="Nika", last_name="Krit")
    result = await service.update(user.id, user_update)
    assert isinstance(result, UserDomain)
    assert result.first_name == "Nika"
    assert result.last_name == "Krit"
    assert result.job_title == user.job_title
    assert result.username == "test"
    assert result.email == user.email
    mock_uow.commit.assert_awaited_once()


def test_update_rejects_job_title():
    with pytest.raises(ValidationError):
        UserUpdate(job_title=UserJobTitle.ANALYST)


@pytest.mark.asyncio
async def test_delete_user(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    await service.delete(user.id)
    mock_uow.users.delete.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_puts_role_into_request(mock_uow):
    mock_uow.users.find_by_email.return_value = None
    mock_uow.refresh.side_effect = _simulate_db_refresh
    service = UserService(mock_uow)
    result = await service.create(make_user_create(job_title=UserJobTitle.DEVELOPER))
    assert result.job_title == UserJobTitle.OTHER
    assert result.requested_job_title == UserJobTitle.DEVELOPER


@pytest.mark.asyncio
async def test_create_other_role_makes_no_request(mock_uow):
    mock_uow.users.find_by_email.return_value = None
    mock_uow.refresh.side_effect = _simulate_db_refresh
    service = UserService(mock_uow)
    result = await service.create(make_user_create(job_title=UserJobTitle.OTHER))
    assert result.job_title == UserJobTitle.OTHER
    assert result.requested_job_title is None


@pytest.mark.asyncio
async def test_request_role_success(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    result = await service.request_role(user.id, UserJobTitle.MANAGER)
    assert result.requested_job_title == UserJobTitle.MANAGER
    assert result.job_title == UserJobTitle.DEVELOPER
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_role_overwrites_open_request(mock_uow):
    user = make_user(requested_job_title=UserJobTitle.MANAGER)
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    result = await service.request_role(user.id, UserJobTitle.ANALYST)
    assert result.requested_job_title == UserJobTitle.ANALYST


@pytest.mark.asyncio
async def test_request_role_already_assigned(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    with pytest.raises(RoleAlreadyAssignedError):
        await service.request_role(user.id, user.job_title)
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_role_requests(mock_uow):
    applicant = make_user(requested_job_title=UserJobTitle.MANAGER)
    mock_uow.users.list_with_role_requests.return_value = [applicant]
    service = UserService(mock_uow)
    result = await service.list_role_requests()
    assert len(result) == 1
    assert isinstance(result[0], UserDomain)
    assert result[0].requested_job_title == UserJobTitle.MANAGER


@pytest.mark.asyncio
async def test_approve_role_success(mock_uow):
    user = make_user(job_title=UserJobTitle.OTHER,
                     requested_job_title=UserJobTitle.MANAGER)
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    result = await service.approve_role(user.id, UserJobTitle.MANAGER)
    assert result.job_title == UserJobTitle.MANAGER
    assert result.requested_job_title is None
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_role_stale_expectation(mock_uow):
    user = make_user(job_title=UserJobTitle.OTHER,
                     requested_job_title=UserJobTitle.MANAGER)
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    with pytest.raises(RoleRequestConflictError):
        await service.approve_role(user.id, UserJobTitle.DEVELOPER)
    assert user.job_title == UserJobTitle.OTHER
    assert user.requested_job_title == UserJobTitle.MANAGER
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_role_without_request(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    with pytest.raises(RoleRequestNotFoundError):
        await service.approve_role(user.id, UserJobTitle.MANAGER)
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_reject_role_keeps_current_role(mock_uow):
    user = make_user(requested_job_title=UserJobTitle.MANAGER)
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    result = await service.reject_role(user.id)
    assert result.job_title == UserJobTitle.DEVELOPER
    assert result.requested_job_title is None
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_role_without_request(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    with pytest.raises(RoleRequestNotFoundError):
        await service.reject_role(user.id)
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_role_success(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    result = await service.set_role(user.id, UserJobTitle.ANALYST)
    assert result.job_title == UserJobTitle.ANALYST
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_role_drops_open_request(mock_uow):
    user = make_user(requested_job_title=UserJobTitle.MANAGER)
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    result = await service.set_role(user.id, UserJobTitle.ANALYST)
    assert result.job_title == UserJobTitle.ANALYST
    assert result.requested_job_title is None


@pytest.mark.asyncio
async def test_delete_discards_the_avatar(mock_uow, mock_storage):
    """The cascade takes the rows; the object in storage has to be dropped by hand."""
    user = make_user(avatar_key="avatars/x.webp")
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow, mock_storage)

    await service.delete(user.id)

    mock_uow.users.delete.assert_awaited_once_with(user)
    mock_storage.delete.assert_awaited_once_with("avatars/x.webp")


@pytest.mark.asyncio
async def test_delete_without_an_avatar_touches_no_storage(mock_uow, mock_storage):
    user = make_user(avatar_key=None)
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow, mock_storage)

    await service.delete(user.id)

    mock_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_survives_a_storage_failure(mock_uow, mock_storage):
    user = make_user(avatar_key="avatars/x.webp")
    mock_uow.users.find_by_id.return_value = user
    mock_storage.delete.side_effect = RuntimeError("storage is down")
    service = UserService(mock_uow, mock_storage)

    await service.delete(user.id)

    mock_uow.commit.assert_awaited_once()
