from pydantic import BaseModel, Field
from datetime import datetime


class TestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the test case")
    status: str = Field(..., description="Status of the test case")
    error_message: str | None = Field(None, description="Error message if the test case failed")
    uploaded_at: datetime = Field(..., description="Upload timestamp of the test case")


class TestResponse(TestCreate):
    id: int = Field(..., description="Unique test case identifier")

    class Config:
        from_attributes = True
