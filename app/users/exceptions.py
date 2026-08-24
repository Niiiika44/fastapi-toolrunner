import uuid

from app.core.exceptions import DomainError


class UserNotFoundError(DomainError):
    def __init__(self, **criteria):
        details = ", ".join(f"{k}={v}" for k, v in criteria.items())
        super().__init__(f"User not found by {details}")


class EmailDomainNotAllowedError(DomainError):
    def __init__(self, email: str):
        super().__init__(f"Email {email} is not allowed")


class UserAlreadyExistsError(DomainError):
    def __init__(self, email: str):
        super().__init__(f"User with email {email} already exists")


class InvalidPasswordError(DomainError):
    def __init__(self):
        super().__init__("Password is invalid")


class RoleRequestNotFoundError(DomainError):
    def __init__(self, user_id: uuid.UUID):
        super().__init__(f"No active role request for user {user_id}")


class RoleRequestConflictError(DomainError):
    def __init__(self, user_id: uuid.UUID):
        super().__init__(f"Role request was changed for user {user_id}")


class RoleAlreadyAssignedError(DomainError):
    def __init__(self, user_id: uuid.UUID):
        super().__init__(f"User {user_id} already has required role")
