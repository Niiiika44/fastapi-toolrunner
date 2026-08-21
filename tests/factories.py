import datetime
import uuid

from app.auth.hash_utils import get_password_hash
from app.memory_allocator.enums import TestStatus, ValidationStatus
from app.memory_allocator.models import Platform, Tag, TestCase, ValidationResult
from app.memory_allocator.schemas import DeadLetterMessage
from app.users.enums import UserJobTitle
from app.users.models import User, UserPermission
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


def make_user(plain_password: str = DEFAULT_PASSWORD, permissions=None, **overrides):
    defaults = dict(
        id=uuid.uuid4(),
        username="test",
        email="test@ispras.ru",
        password=get_password_hash(plain_password),
        first_name="Nikita",
        last_name="Lebedev",
        job_title=UserJobTitle.DEVELOPER,
        is_superuser=False
    )
    user = User(**{**defaults, **overrides})
    user.permissions = make_permissions(permissions)
    return user


def make_permissions(permissions=None) -> list[UserPermission]:
    return [UserPermission(permission=str(name)) for name in permissions or []]


def make_platform(**overrides):
    defaults = dict(
        id=1,
        mmu_family="mips_r6000",
        page_size=4096,
        config={},
        created_at=datetime.datetime.now(datetime.UTC),
    )
    return Platform(**{**defaults, **overrides})


def make_test(**overrides):
    defaults = dict(
        id=1,
        name="default_test",
        status=TestStatus.PARSED,
        error_message=None,
        uploaded_at=datetime.datetime.now(datetime.UTC),
        uploaded_by_id=uuid.uuid4(),
        module_count=0,
        block_count=0,
        kernel_entry_count=0,
        user_entry_count=0,
        platform=make_platform(),
        uploaded_by=make_user()
    )
    return TestCase(**{**defaults, **overrides})


def make_validation_result(**overrides):
    defaults = dict(
        id=1,
        test_id=1,
        valid=None,
        status=ValidationStatus.PENDING,
        schema_valid=None,
        errors=None,
        checker_version="mock-1.0",
        checked_at=datetime.datetime.now(datetime.UTC),
        requested_at=datetime.datetime.now(datetime.UTC),
        test=make_test()
    )
    return ValidationResult(**{**defaults, **overrides})


def make_tag(**overrides):
    defaults = dict(
        id=1,
        name="default_tag"
    )
    return Tag(**{**defaults, **overrides})


def make_message(**overrides) -> DeadLetterMessage:
    defaults = dict(
        task_name="memory_allocator.process_test",
        task_id="task-uuid",
        args=[7],
        request_id=None,
        reason="delivery_limit",
        delivered_count=1,
    )
    return DeadLetterMessage(**{**defaults, **overrides})
