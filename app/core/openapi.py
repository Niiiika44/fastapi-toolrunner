from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    message: str = Field(..., description="Error description")


class ErrorResponse(BaseModel):
    """Single error format of the API. Produced by core/error_handler."""
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"error": {"message": "Test is not found"}}]}
    )
    error: ErrorBody = Field(..., description="Error envelope")


def error(description: str) -> dict[str, Any]:
    return {"model": ErrorResponse, "description": description}
