from enum import Enum


class UserJobTitle(str, Enum):
    """
    Job title of user
    """
    DEVELOPER = "developer"
    TESTER = "tester"
    ANALYST = "analyst"
    MANAGER = "manager"
    OTHER = "other"

    def __str__(self):
        return self.value
