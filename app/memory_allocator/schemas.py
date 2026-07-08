import uuid
from datetime import datetime

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
