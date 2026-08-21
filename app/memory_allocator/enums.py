from enum import StrEnum


class TestStatus(StrEnum):
    """
    Parsing lifecycle of a test case: PENDING -> PROCESSING -> PARSED | ERROR.

    PENDING – the upload is accepted and the parsing task is queued.
    PROCESSING – a worker is parsing the archive.
    PARSED – terminal, the test case is ready to be validated and exported.
    ERROR – terminal, parsing failed; `error_message` tells why.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    PARSED = "parsed"
    ERROR = "error"


class ValidationStatus(StrEnum):
    """
    Lifecycle of one checker run: PENDING -> RUNNING -> COMPLETED | FAILED.

    PENDING – the run is queued.
    RUNNING – the checker is working on the test case.
    COMPLETED – terminal, the checker finished; `valid` holds the verdict.
    FAILED – terminal, the checker itself broke; the verdict is unknown.
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ArtifactKind(StrEnum):
    """Role of a single file extracted from an uploaded test case archive."""
    CONFIG = "config"
    SHARED_GROUPS = "shared_groups"
    INPUT_CONSTRAINTS = "input_constraints"
    INPUT_ARCH = "input_arch"
    OUTPUT_ARCH = "output_arch"
    OUTPUT_VDEFINITIONS = "output_vdefinitions"
    LOG = "log"
    STATUS = "status"
