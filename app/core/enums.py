from enum import Enum


class InputType(str, Enum):
    """
    Supported types of input
    """
    YAML = "yaml"
    JSON = "json"

    def __str__(self):
        return self.value


class TestStatus(str, Enum):
    """
    Status of test processing
    """
    PENDING = "pending"
    PARSED = "parsed"
    ERROR = "error"

    def __str__(self):
        return self.value
