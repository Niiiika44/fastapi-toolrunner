import pytest

from app.auth.enums import Permission
from app.auth.permissions import ROLE_PERMISSIONS, resolve_permissions
from app.users.enums import UserJobTitle

BASELINE = {Permission.TEST_READ, Permission.PLATFORM_READ}


@pytest.mark.parametrize(
    ("job_title", "expected"),
    [
        (UserJobTitle.DEVELOPER, BASELINE | {
            Permission.TEST_UPLOAD, Permission.TEST_VALIDATE,
            Permission.TEST_EXPORT, Permission.TEST_TAG, Permission.TAG_MANAGE,
        }),
        (UserJobTitle.TESTER, BASELINE | {
            Permission.TEST_UPLOAD, Permission.TEST_VALIDATE,
            Permission.TEST_EXPORT, Permission.TEST_TAG, Permission.TAG_MANAGE,
        }),
        (UserJobTitle.ANALYST, BASELINE | {Permission.TEST_EXPORT, Permission.TEST_TAG}),
        (UserJobTitle.MANAGER, BASELINE | {Permission.TEST_EXPORT, Permission.USER_READ_ANY}),
        (UserJobTitle.OTHER, BASELINE),
    ],
)
def test_role_gives_exactly_its_permissions(job_title, expected):
    assert resolve_permissions(job_title) == expected


def test_unknown_job_title_gives_no_permissions():
    assert resolve_permissions("architect") == frozenset()


def test_unknown_job_title_still_honours_individual_grants():
    assert resolve_permissions("architect", [Permission.TEST_UPLOAD]) == {Permission.TEST_UPLOAD}


def test_grant_adds_permission_on_top_of_the_role():
    granted = resolve_permissions(UserJobTitle.ANALYST, [Permission.TEST_UPLOAD])

    assert Permission.TEST_UPLOAD in granted
    assert granted == resolve_permissions(UserJobTitle.ANALYST) | {Permission.TEST_UPLOAD}


def test_grant_duplicating_the_role_changes_nothing():
    assert (
        resolve_permissions(UserJobTitle.MANAGER, [Permission.TEST_READ])
        == resolve_permissions(UserJobTitle.MANAGER)
    )


def test_unknown_grant_is_skipped_while_the_valid_one_applies():
    granted = resolve_permissions(UserJobTitle.OTHER, ["test:teleport", Permission.TEST_EXPORT])

    assert granted == BASELINE | {Permission.TEST_EXPORT}


def test_empty_grants_give_exactly_the_role():
    assert resolve_permissions(UserJobTitle.TESTER, []) == resolve_permissions(UserJobTitle.TESTER)


def test_permissions_are_immutable():
    assert isinstance(resolve_permissions(UserJobTitle.DEVELOPER), frozenset)
    assert all(isinstance(perms, frozenset) for perms in ROLE_PERMISSIONS.values())


def test_every_job_title_is_present_in_the_matrix():
    assert set(ROLE_PERMISSIONS) == set(UserJobTitle)


def test_plain_string_job_title_resolves_like_the_enum_member():
    assert resolve_permissions("developer") == resolve_permissions(UserJobTitle.DEVELOPER)
    assert resolve_permissions("developer") != frozenset()
