import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.memory_allocator.enums import TestStatus


class PlatformResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    mmu_family: str = Field(..., description="MMU family")
    page_size: int = Field(..., description="Page size")


class UploaderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(..., description="Uploader id")
    email: EmailStr = Field(..., description="Uploader email")
    first_name: str = Field(..., description="Uploader first name")
    last_name: str = Field(..., description="Uploader last name")


class TestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique test case identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Name of the test case")
    status: TestStatus = Field(..., description="Status of the test case")
    error_message: str | None = Field(None, description="Error message if the test case failed")
    uploaded_at: datetime = Field(..., description="Upload timestamp of the test case")
    module_count: int = Field(..., description="Number of modules in test")
    block_count: int = Field(..., description="Number of blocks in all modules")
    kernel_entry_count: int = Field(..., description="Number of kernel mapping entries")
    user_entry_count: int = Field(..., description="Number of user mapping entries")
    platform: PlatformResponse = Field(..., description="Platform of the test")
    uploaded_by: UploaderResponse = Field(..., description="Who uploaded the test")
