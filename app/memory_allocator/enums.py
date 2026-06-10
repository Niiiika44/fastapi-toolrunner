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


class ArtifactKind(str, Enum):
    """
    Contents of one single test
    """
    CONFIG = "config"
    SHARED_GROUPS = "shared_groups"
    INPUT_CONSTRAINTS = "input_constraints"
    INPUT_ARCH = "input_arch"
    OUTPUT_ARCH = "output_arch"
    OUTPUT_VDEFINITIONS = "output_vdefinitions"
    LOG = "log"
    STATUS = "status"
