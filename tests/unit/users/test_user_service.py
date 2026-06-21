import uuid

import pytest

from app.auth.hash_utils import verify_password
from app.users.enums import UserJobTitle
from app.users.exceptions import (
    EmailDomainNotAllowedError,
    InvalidPasswordError,
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
    user_update = UserUpdate(job_title=UserJobTitle.ANALYST)
    result = await service.update(user.id, user_update)
    assert isinstance(result, UserDomain)
    assert result.job_title == UserJobTitle.ANALYST
    assert result.username == "test"
    assert result.email == user.email
    assert result.first_name == user.first_name
    assert result.last_name == user.last_name
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_user(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    await service.delete(user.id)
    mock_uow.users.delete.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()
