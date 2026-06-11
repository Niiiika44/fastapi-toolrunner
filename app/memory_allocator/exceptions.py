from app.core.exceptions import DomainError


class InvalidUploadError(DomainError):
    def __init__(self, test_name: str):
        super().__init__(f"Test {test_name} could not be processed")


class ParsingError(DomainError):
    def __init__(self, filename: str):
        super().__init__(f"File {filename} could not be parsed")


class EmptyFileError(DomainError):
    def __init__(self):
        super().__init__("File is empty")


class TestNotFoundError(DomainError):
    def __init__(self, test_id: int):
        super().__init__(f"Test id {test_id} does not exist")


class PlatformExtractionError(DomainError):
    def __init__(self):
        super().__init__("Platform cannot be extracted")
