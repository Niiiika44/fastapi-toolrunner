from enum import Enum


class InputType(str, Enum):
    """
    supported types of input
    """
    YAML = "yaml"
    JSON = "json"

    def __str__(self):
        return self.value
