from collections.abc import Iterable

from app.auth.enums import Permission
from app.users.enums import UserJobTitle

KNOWN_PERMISSIONS: frozenset[Permission] = frozenset(Permission)

ROLE_PERMISSIONS: dict[UserJobTitle, frozenset[Permission]] = {
    UserJobTitle.DEVELOPER: frozenset(
        [
            Permission.TEST_READ,
            Permission.PLATFORM_READ,
            Permission.TEST_UPLOAD,
            Permission.TEST_VALIDATE,
            Permission.TEST_TAG,
            Permission.TEST_EXPORT,
            Permission.TAG_MANAGE
        ]
    ),
    UserJobTitle.TESTER: frozenset(
        [
            Permission.TEST_READ,
            Permission.PLATFORM_READ,
            Permission.TEST_UPLOAD,
            Permission.TEST_VALIDATE,
            Permission.TEST_TAG,
            Permission.TEST_EXPORT,
            Permission.TAG_MANAGE
        ]
    ),
    UserJobTitle.ANALYST: frozenset(
        [
            Permission.TEST_READ,
            Permission.PLATFORM_READ,
            Permission.TEST_TAG,
            Permission.TEST_EXPORT
        ]
    ),
    UserJobTitle.MANAGER: frozenset(
        [
            Permission.TEST_READ,
            Permission.PLATFORM_READ,
            Permission.TEST_EXPORT,
            Permission.USER_READ_ANY
        ]
    ),
    UserJobTitle.OTHER: frozenset(
        [
            Permission.TEST_READ,
            Permission.PLATFORM_READ
        ]
    ),
}


def resolve_permissions(job_title: str, granted: Iterable[str] = ()) -> frozenset[Permission]:
    baseline = ROLE_PERMISSIONS.get(job_title, frozenset())
    individual = {Permission(name) for name in granted if name in KNOWN_PERMISSIONS}
    return baseline | individual
