import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.memory_allocator.enums import TestStatus, ValidationStatus


class PlatformDomain(BaseModel):
    """Доменная модель платформы."""
    model_config = ConfigDict(from_attributes=True)

    mmu_family: str = Field(..., description="MMU family")
    page_size: int = Field(..., description="Page size")


class PlatformResponse(PlatformDomain):
    """API-ответ платформы."""


class UploaderDomain(BaseModel):
    """Доменная модель автора загрузки."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Uploader id")
    email: EmailStr = Field(..., description="Uploader email")
    first_name: str = Field(..., description="Uploader first name")
    last_name: str = Field(..., description="Uploader last name")


class UploaderResponse(UploaderDomain):
    """API-ответ автора."""


class TestReadBase(BaseModel):
    """Общие read-поля тест-кейса."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique test case identifier")
    name: str = Field(..., description="Name of the test case")
    status: TestStatus = Field(..., description="Status of the test case")
    error_message: str | None = Field(None, description="Error message if the test case failed")
    uploaded_at: datetime = Field(..., description="Upload timestamp of the test case")
    module_count: int = Field(..., description="Number of modules in test")
    block_count: int = Field(..., description="Number of blocks in all modules")
    kernel_entry_count: int = Field(..., description="Number of kernel mapping entries")
    user_entry_count: int = Field(..., description="Number of user mapping entries")


class TestDomain(TestReadBase):
    """Доменная модель тест-кейса."""
    platform: PlatformDomain
    uploaded_by: UploaderDomain


class TestResponse(TestReadBase):
    """API-ответ тест-кейса."""
    platform: PlatformResponse
    uploaded_by: UploaderResponse


class ValidationReadBase(BaseModel):
    """Общие read-поля валидации теста."""
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
    """Доменная модель валидации теста."""


class ValidationResponse(ValidationDomain):
    """API-ответ валидации теста."""


class PlatformDetailDomain(PlatformDomain):
    """Доменная модель платформы с расширенным списком полей."""
    id: int
    config: dict | None = None
    created_at: datetime


class PlatformDetailResponse(PlatformDetailDomain):
    """API-ответ детальной платформы."""


class TagReadBase(BaseModel):
    """Общие read-поля тэга теста."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Tag id")
    name: str = Field(..., description="Name of the tag")


class TagDomain(TagReadBase):
    """Доменная модель тэга теста."""


class TagResponse(TagDomain):
    """API-ответ тэга теста."""


class TagCreate(BaseModel):
    """Входная модель создания тэга."""
    name: str = Field(..., min_length=2, max_length=50,
                      description="Name of the tag, from 2 to 50 symbols")


class TestFilter(BaseModel):
    """Входная модель фильтрации тестовых примеров."""
    statuses: list[TestStatus] | None = Field(None, description="Statuses of the test case")
    name: str | None = Field(None, description="Approximate name of the test case")
    platform_ids: list[int] | None = Field(None, description="Unique platform identifiers")
    tags: list[str] | None = Field(None, description="Related tags")
    mine: bool = Field(False, description="Test cases uploaded by me")


class Pagination(BaseModel):
    """Входная модель пагинации."""
    limit: int = Field(100, ge=1, le=200)
    offset: int = Field(0, ge=0)


class TestPagination(Pagination):
    """Входная модель пагинации тестовых примеров."""


class DeadLetterPagination(Pagination):
    """Входная модель пагинации сообщений из dead-letter-queue."""


class TestListQuery(TestFilter, TestPagination):
    """Входная модель фильтрации и пагинации тестовых примеров."""


class PaginatedTestsResponse(BaseModel):
    """API-ответ фильтрации тестов."""
    tests: list[TestResponse] = Field(..., description="Tests matching filtering")
    total: int = Field(..., description="Total amount of tests")
    limit: int = Field(100, ge=1, le=200)
    offset: int = Field(0, ge=0)


class TestStatusEvent(BaseModel):
    """Событие смены статуса разбора тест-кейса (WS/pub-sub)."""
    model_config = ConfigDict(frozen=True)

    event: Literal["test.status"] = "test.status"
    test_id: int = Field(..., description="Test unique identifier")
    status: TestStatus = Field(..., description="Status of the test case")
    error_message: str | None = Field(None, description="Error message if the test case failed")
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Event timestamp")


class ValidationStatusEvent(BaseModel):
    """Событие смены статуса валидации тест-кейса (WS/pub-sub)."""
    model_config = ConfigDict(frozen=True)

    event: Literal["validation.status"] = "validation.status"
    test_id: int = Field(..., description="Test unique identifier")
    validation_id: int = Field(..., description="Test validation unique identifier")
    status: ValidationStatus = Field(..., description="Status of the test case validation")
    valid: bool | None = Field(None, description="If test is valid")
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Event timestamp")


class DeadLetterMessage(BaseModel):
    """Доменная модель письма из очереди dead_letter_queue."""
    model_config = ConfigDict(frozen=True)

    task_name: str = Field(..., description="Name of the failed task")
    task_id: str = Field(..., description="Failed task unique identifier")
    args: list | None = Field(None, description="Failed task positional arguments")
    request_id: str | None = Field(None, description="Request unique identifier")
    reason: str | None = Field(None, description="Why the broker moved the message aside")
    delivered_count: int | None = Field(None, description="How many times it was delivered")
