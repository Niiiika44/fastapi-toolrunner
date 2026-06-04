from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Схема для ответа с токеном"""
    access_token: str = Field(..., description="JWT токен доступа")
    token_type: str = Field(..., description="Тип токена")
