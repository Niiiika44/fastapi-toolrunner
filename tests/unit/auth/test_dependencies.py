import logging

import pytest

from app.auth.dependencies import has_permissions
from app.auth.enums import Permission
from app.users.enums import UserJobTitle
from tests.factories import make_user

UNKNOWN = "test:teleport"


def test_permission_from_the_role_is_allowed():
    user = make_user(job_title=UserJobTitle.ANALYST)

    assert has_permissions(user, [Permission.TEST_EXPORT])


def test_permission_from_an_individual_grant_is_allowed():
    user = make_user(job_title=UserJobTitle.ANALYST, permissions=[Permission.TEST_UPLOAD])

    assert has_permissions(user, [Permission.TEST_UPLOAD])


def test_permission_the_user_does_not_have_is_denied():
    user = make_user(job_title=UserJobTitle.ANALYST)

    assert not has_permissions(user, [Permission.TEST_UPLOAD])


def test_superuser_bypasses_the_check():
    user = make_user(job_title=UserJobTitle.OTHER, is_superuser=True)

    assert has_permissions(user, [Permission.TAG_MANAGE, Permission.USER_DELETE_ANY])


def test_all_required_permissions_must_be_present():
    user = make_user(job_title=UserJobTitle.ANALYST)

    assert has_permissions(user, [Permission.TEST_READ, Permission.TEST_EXPORT])
    assert not has_permissions(user, [Permission.TEST_READ, Permission.TEST_UPLOAD])


def test_empty_requirement_is_allowed():
    user = make_user(job_title=UserJobTitle.OTHER)

    assert has_permissions(user, [])


def test_unknown_grant_is_ignored_while_the_valid_one_applies():
    user = make_user(job_title=UserJobTitle.OTHER, permissions=[UNKNOWN, Permission.TEST_EXPORT])

    assert has_permissions(user, [Permission.TEST_EXPORT])
    assert not has_permissions(user, [Permission.TAG_MANAGE])


def test_unknown_grant_is_logged(caplog):
    user = make_user(job_title=UserJobTitle.OTHER, permissions=[UNKNOWN])

    with caplog.at_level(logging.WARNING):
        has_permissions(user, [Permission.TEST_READ])

    records = [r for r in caplog.records if r.getMessage() == "user.unknown_permission"]
    assert len(records) == 1
    assert records[0].levelname == "WARNING"
    assert records[0].permission == UNKNOWN
    assert records[0].user_id == str(user.id)


def test_superuser_grants_are_not_read_at_all():
    user = make_user(is_superuser=True, permissions=[UNKNOWN])

    assert has_permissions(user, [Permission.TAG_MANAGE])


@pytest.mark.parametrize(
    ("job_title", "permission", "expected"),
    [
        (UserJobTitle.DEVELOPER, Permission.TAG_MANAGE, True),
        (UserJobTitle.TESTER, Permission.TEST_VALIDATE, True),
        (UserJobTitle.ANALYST, Permission.TAG_MANAGE, False),
        (UserJobTitle.MANAGER, Permission.USER_READ_ANY, True),
        (UserJobTitle.MANAGER, Permission.TEST_UPLOAD, False),
        (UserJobTitle.OTHER, Permission.TEST_READ, True),
        (UserJobTitle.OTHER, Permission.TEST_EXPORT, False),
    ],
)
def test_matrix_reaches_the_orm_layer(job_title, permission, expected):
    user = make_user(job_title=job_title)

    assert has_permissions(user, [permission]) is expected
