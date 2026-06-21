import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.memory_allocator.enums import TestStatus


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
