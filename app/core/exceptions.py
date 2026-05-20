class DomainError(Exception):
    """Base class for all domain-level exceptions."""
    def __init__(self, message: str | None = None):
        self.message = message or self.__class__.__name__
        super().__init__(self.message)
