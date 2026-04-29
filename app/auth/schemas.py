from pydantic import BaseModel, Field, EmailStr


class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=8, max_length=50,
                          description="Пароль, от 8 до 50 символов")


class TokenResponse(BaseModel):
    """Схема для ответа с токеном"""
    access_token: str = Field(..., description="JWT токен доступа")
    token_type: str = Field(..., description="Тип токена")

