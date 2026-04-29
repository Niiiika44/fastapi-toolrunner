from enum import Enum


class TestStatus(str, Enum):
    """
    Status of test processing
    """
    PENDING = "pending"
    PARSED = "parsed"
    ERROR = "error"

    def __str__(self):
        return self.value
