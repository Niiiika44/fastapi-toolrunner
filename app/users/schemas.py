import uuid
from pydantic import BaseModel, Field, EmailStr
from app.users.enums import UserJobTitle


class UserCreate(BaseModel):
    """Схема для регистрации пользователя"""
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=8, max_length=50,
                          description="Пароль, от 8 до 50 символов")
    first_name: str = Field(..., min_length=2, max_length=50,
                            description="Имя пользователя")
    last_name: str = Field(..., min_length=2, max_length=50,
                           description="Фамилия пользователя")
    job_title: UserJobTitle = Field(..., description="Должность пользователя")


class UserUpdate(BaseModel):
    """Схема для обновления данных пользователя"""
    first_name: str | None = Field(None, min_length=2, max_length=50,
                                   description="Имя пользователя")
    last_name: str | None = Field(None, min_length=2, max_length=50,
                                  description="Фамилия пользователя")
    job_title: UserJobTitle | None = Field(None, description="Должность пользователя")


class ChangePassword(BaseModel):
    """Схема для обновления пароля пользователя"""
    old_password: str = Field(..., min_length=8, max_length=50,
                              description="Старый пароль")
    new_password: str = Field(..., min_length=8, max_length=50,
                              description="Новый пароль")


class ChangeEmail(BaseModel):
    """Схема для обновления электронной почты пользователя"""
    password: str = Field(..., min_length=8, max_length=50,
                          description="Пароль пользователя")
    new_email: EmailStr = Field(..., description="Новая электронная почта")


class UserResponse(BaseModel):
    """Схема для ответа с данными пользователя"""
    id: uuid.UUID = Field(..., description="Уникальный идентификатор пользователя")
    email: EmailStr = Field(..., description="Электронная почта")
    first_name: str = Field(..., description="Имя пользователя")
    last_name: str = Field(..., description="Фамилия пользователя")
    job_title: UserJobTitle = Field(..., description="Должность пользователя")
    is_superuser: bool = Field(..., description="Является ли пользователь суперпользователем")

    class Config:
        from_attributes = True
