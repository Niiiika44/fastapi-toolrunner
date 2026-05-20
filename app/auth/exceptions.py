from app.core.exceptions import DomainError


class InvalidCredentialsError(DomainError):
    def __init__(self):
        super().__init__("Credentials are invalid")


class InvalidTokenError(DomainError):
    def __init__(self):
        super().__init__("Invalid or expired token")


class NotEnoughPermissionsError(DomainError):
    def __init__(self):
        super().__init__("Not enough permissions")
