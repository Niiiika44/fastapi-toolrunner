import uuid

import pytest

from app.auth.hash_utils import get_password_hash, verify_password
from app.users.enums import UserJobTitle
from app.users.exceptions import (
    EmailDomainNotAllowedError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.users.models import User
from app.users.schemas import UserCreate, UserUpdate
from app.users.services import UserService

DEFAULT_PASSWORD = "password"


def make_user_create(**overrides):
    defaults = dict(
        email="test@ispras.ru",
        password=DEFAULT_PASSWORD,
        first_name="Nikita",
        last_name="Lebedev",
        job_title=UserJobTitle.DEVELOPER
    )
    return UserCreate(**{**defaults, **overrides})


def make_user(plain_password: str = DEFAULT_PASSWORD, **overrides):
    defaults = dict(
        id=uuid.uuid4(),
        username="test",
        email="test@ispras.ru",
        password=get_password_hash(plain_password),
        first_name="Nikita",
        last_name="Lebedev",
        job_title=UserJobTitle.DEVELOPER,
    )
    return User(**{**defaults, **overrides})


@pytest.mark.asyncio
async def test_create_success(mock_uow):
    mock_uow.users.find_by_email.return_value = None
    service = UserService(mock_uow)
    result = await service.create(make_user_create())
    assert isinstance(result, User)
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
    service = UserService(mock_uow)
    user_data = make_user_create()
    created_user = await service.create(user_data)
    assert created_user.password != user_data.password
    assert verify_password("password", created_user.password)


@pytest.mark.asyncio
async def test_create_username(mock_uow):
    mock_uow.users.find_by_email.return_value = None
    service = UserService(mock_uow)
    created_user = await service.create(make_user_create())
    assert created_user.username == "test"


@pytest.mark.asyncio
async def test_get_by_id_existing_user(mock_uow):
    mock_uow.users.find_by_id.return_value = User()
    service = UserService(mock_uow)
    random_uuid = uuid.uuid4()
    existing_user = await service.get_by_id(random_uuid)
    assert existing_user is not None
    assert isinstance(existing_user, User)


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
    existing_user = await service.change_password(
        user.id, DEFAULT_PASSWORD, "new_password"
    )
    assert isinstance(existing_user, User)
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
    changed_email_user = await service.change_email(
        user.id, new_email, DEFAULT_PASSWORD
    )
    assert isinstance(changed_email_user, User)
    assert changed_email_user.email == new_email
    assert changed_email_user.username == "new_email"
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_same_email(mock_uow):
    email = "test@ispras.ru"
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    changed_email_user = await service.change_email(
        user.id, email, DEFAULT_PASSWORD
    )
    assert changed_email_user == user
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
    updated_user = await service.update(user.id, user_update)
    assert updated_user.job_title == UserJobTitle.ANALYST
    assert updated_user.username == user.username
    assert updated_user.email == user.email
    assert updated_user.password == user.password
    assert updated_user.first_name == user.first_name
    assert updated_user.last_name == user.last_name
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_user(mock_uow):
    user = make_user()
    mock_uow.users.find_by_id.return_value = user
    service = UserService(mock_uow)
    await service.delete(user.id)
    mock_uow.users.delete.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()
