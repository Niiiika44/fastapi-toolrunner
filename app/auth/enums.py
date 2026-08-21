from enum import StrEnum


class Permission(StrEnum):
    """User permissions (depends on user role)."""
    TAG_MANAGE = "tag:manage"
    PLATFORM_READ = "platform:read"
    TEST_READ = "test:read"
    TEST_UPLOAD = "test:upload"
    TEST_VALIDATE = "test:validate"
    TEST_EXPORT = "test:export"
    TEST_TAG = "test:tag"
    USER_READ_ANY = "user:read_any"
    USER_UPDATE_ANY = "user:update_any"
    USER_DELETE_ANY = "user:delete_any"
