from app.core.exceptions import DomainError


class InvalidUploadError(DomainError):
    def __init__(self, test_name: str, info: str):
        super().__init__(f"Test {test_name} could not be processed: {info}")


class ParsingError(DomainError):
    def __init__(self, exc: str):
        super().__init__(f"File could not be parsed: {exc}")


class EmptyFileError(DomainError):
    def __init__(self, filename: str):
        super().__init__(f"File {filename} is empty")


class TestNotFoundError(DomainError):
    def __init__(self, test_id: int):
        super().__init__(f"Test id {test_id} does not exist")


class PlatformExtractionError(DomainError):
    def __init__(self):
        super().__init__("Platform cannot be extracted")


class TestNotValidatableError(DomainError):
    def __init__(self, test_id: int, status: str):
        super().__init__(f"Test id {test_id} is not validatable (status: {status})")


class TagAlreadyExistsError(DomainError):
    def __init__(self, tag_name: str):
        super().__init__(f"Tag {tag_name} is not unique")


class TagNotFoundError(DomainError):
    def __init__(self, tag_id: int):
        super().__init__(f"Tag with id {tag_id} does not exist")


class PlatformNotFoundError(DomainError):
    def __init__(self, platform_id: int):
        super().__init__(f"Platform with id {platform_id} does not exist")
