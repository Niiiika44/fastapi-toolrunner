import pytest

from app.users.enums import UserJobTitle
from app.users.exceptions import EmailDomainNotAllowedError, UserAlreadyExistsError
from app.users.models import User
from app.users.schemas import UserCreate
from app.users.services import UserService


def make_user_create(**overrides):
    defaults = dict(email="test@ispras.ru", password="password",
                    first_name="Nikita", last_name="Lebedev",
                    job_title=UserJobTitle.DEVELOPER)
    return UserCreate(**{**defaults, **overrides})


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


@pytest.mark.asyncio
async def test_create_username(mock_uow):
    mock_uow.users.find_by_email.return_value = None
    service = UserService(mock_uow)
    created_user = await service.create(make_user_create())
    assert created_user.username == "test"
