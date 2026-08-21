import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.memory_allocator.enums import TestStatus, ValidationStatus


class PlatformDomain(BaseModel):
    """Service-layer platform model."""
    model_config = ConfigDict(from_attributes=True)

    mmu_family: str = Field(..., description="MMU family", examples=["mips_r6000"])
    page_size: int = Field(..., description="Page size in bytes", examples=[4096])


class PlatformResponse(PlatformDomain):
    """Platform as nested into a test case."""


class UploaderDomain(BaseModel):
    """Service-layer model of the user who uploaded a test case."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Uploader id")
    email: EmailStr = Field(..., description="Uploader email")
    first_name: str = Field(..., description="Uploader first name")
    last_name: str = Field(..., description="Uploader last name")


class UploaderResponse(UploaderDomain):
    """Author of the upload as nested into a test case."""


class TestReadBase(BaseModel):
    """Fields every representation of a test case exposes."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique test case identifier")
    name: str = Field(..., description="Name of the test case")
    status: TestStatus = Field(..., description="Status of the test case")
    error_message: str | None = Field(None, description="Error message if the test case failed")
    uploaded_at: datetime = Field(..., description="Upload timestamp of the test case")
    module_count: int = Field(
        ..., description="Number of modules in test; zero until the archive is parsed"
    )
    block_count: int = Field(
        ..., description="Number of blocks in all modules; zero until the archive is parsed"
    )
    kernel_entry_count: int = Field(
        ..., description="Number of kernel mapping entries; zero until the archive is parsed"
    )
    user_entry_count: int = Field(
        ..., description="Number of user mapping entries; zero until the archive is parsed"
    )


class TestDomain(TestReadBase):
    """Service-layer test case model."""
    platform: PlatformDomain = Field(..., description="Platform the test case was built for")
    uploaded_by: UploaderDomain = Field(..., description="User who uploaded the test case")


class TestResponse(TestReadBase):
    """Test case as returned by the API. Counters stay zero until the status becomes PARSED."""
    platform: PlatformResponse = Field(..., description="Platform the test case was built for")
    uploaded_by: UploaderResponse = Field(..., description="User who uploaded the test case")


class ValidationReadBase(BaseModel):
    """Fields every representation of a validation result exposes."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique validation result identifier")
    status: ValidationStatus = Field(..., description="Status of the validation result")
    valid: bool | None = Field(None, description="If test is valid")
    schema_valid: bool | None = Field(None, description="If test files are compatible with schema")
    errors: list | None = Field(None, description="Validation errors spot by checker")
    checker_version: str | None = Field(None, description="Version of used validating tool")
    checked_at: datetime | None = Field(
        None, description="Validation timestamp of the checked test case"
    )
    test_id: int = Field(..., description="Unique checked test case identifier")


class ValidationDomain(ValidationReadBase):
    """Service-layer validation result model."""


class ValidationResponse(ValidationDomain):
    """One checker run. Fields other than the status stay empty until the run completes."""


class PlatformDetailDomain(PlatformDomain):
    """Service-layer platform model with the fields omitted from the nested representation."""
    id: int = Field(..., description="Unique platform identifier")
    config: dict | None = Field(
        None, description="Raw memin.yaml of the first upload that introduced this platform"
    )
    created_at: datetime = Field(..., description="Timestamp the platform was first seen at")


class PlatformDetailResponse(PlatformDetailDomain):
    """Platform as returned by the platform endpoints."""


class TagReadBase(BaseModel):
    """Fields every representation of a tag exposes."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Tag id")
    name: str = Field(..., description="Name of the tag")


class TagDomain(TagReadBase):
    """Service-layer tag model."""


class TagResponse(TagDomain):
    """Tag as returned by the API."""


class ArtifactLinkDomain(BaseModel):
    """Artifact handed over as a link to the storage."""
    model_config = ConfigDict(frozen=True)

    filename: str = Field(..., description="Name of the file")
    url: str = Field(..., description="Presigned url")


class ArtifactContentDomain(BaseModel):
    """Artifact handed over as bytes."""
    model_config = ConfigDict(frozen=True)

    filename: str = Field(..., description="Name of the file")
    content: bytes = Field(..., description="Artifact content")


class TagCreate(BaseModel):
    """Tag creation request. Tag names are unique across the service."""
    name: str = Field(..., min_length=2, max_length=50,
                      description="Name of the tag, from 2 to 50 symbols",
                      examples=["regression"])


class TestFilter(BaseModel):
    """Test case filters. Values of one list filter combine as OR, different filters as AND."""
    statuses: list[TestStatus] | None = Field(
        None, description="Statuses of the test case", examples=[["parsed", "error"]]
    )
    name: str | None = Field(
        None, description="Case-insensitive substring of the test case name"
    )
    platform_ids: list[int] | None = Field(
        None, description="Unique platform identifiers", examples=[[1, 2]]
    )
    tags: list[str] | None = Field(
        None, description="Related tags", examples=[["regression", "mips"]]
    )
    mine: bool = Field(False, description="Test cases uploaded by me")


class Pagination(BaseModel):
    """Page window of a listing."""
    limit: int = Field(100, ge=1, le=200, description="Maximum number of items to return")
    offset: int = Field(0, ge=0, description="Number of items to skip")


class TestPagination(Pagination):
    """Page window of a test case listing."""


class DeadLetterPagination(Pagination):
    """Page window of a dead-letter-queue listing."""


class TestListQuery(TestFilter, TestPagination):
    """Filters and page window of a test case listing."""


class PaginatedTestsResponse(BaseModel):
    """One page of test cases. `total` counts every match of the filters, ignoring the window."""
    tests: list[TestResponse] = Field(..., description="Tests matching filtering")
    total: int = Field(..., description="Total amount of tests matching the filters")
    limit: int = Field(100, ge=1, le=200, description="Maximum number of items returned")
    offset: int = Field(0, ge=0, description="Number of items skipped")


class TestStatusEvent(BaseModel):
    """Parsing status change of a test case, pushed over the status WebSocket."""
    model_config = ConfigDict(frozen=True)

    event: Literal["test.status"] = "test.status"
    test_id: int = Field(..., description="Test unique identifier")
    status: TestStatus = Field(..., description="Status of the test case")
    error_message: str | None = Field(None, description="Error message if the test case failed")
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Event timestamp")


class ValidationStatusEvent(BaseModel):
    """Validation status change of a test case, pushed over the status WebSocket."""
    model_config = ConfigDict(frozen=True)

    event: Literal["validation.status"] = "validation.status"
    test_id: int = Field(..., description="Test unique identifier")
    validation_id: int = Field(..., description="Test validation unique identifier")
    status: ValidationStatus = Field(..., description="Status of the test case validation")
    valid: bool | None = Field(None, description="If test is valid")
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Event timestamp")


class DeadLetterMessage(BaseModel):
    """Service-layer model of a message taken out of the dead-letter queue."""
    model_config = ConfigDict(frozen=True)

    task_name: str = Field(..., description="Name of the failed task")
    task_id: str = Field(..., description="Failed task unique identifier")
    args: list | None = Field(None, description="Failed task positional arguments")
    request_id: str | None = Field(None, description="Request unique identifier")
    reason: str | None = Field(None, description="Why the broker moved the message aside")
    delivered_count: int | None = Field(None, description="How many times it was delivered")
