from enum import StrEnum


class TestStatus(StrEnum):
    """
    Status of test processing
    """
    PENDING = "pending"
    PROCESSING = "processing"
    PARSED = "parsed"
    ERROR = "error"


class ArtifactKind(StrEnum):
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
