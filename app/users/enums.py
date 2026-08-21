from enum import StrEnum


class UserJobTitle(StrEnum):
    """Job title of a user."""
    DEVELOPER = "developer"
    TESTER = "tester"
    ANALYST = "analyst"
    MANAGER = "manager"
    OTHER = "other"
