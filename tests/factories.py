import uuid

from app.auth.hash_utils import get_password_hash
from app.users.enums import UserJobTitle
from app.users.models import User
from app.users.schemas import UserCreate

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
