from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Issued access token. Authorizes both the HTTP endpoints and the status WebSocket."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type, always `bearer`")
