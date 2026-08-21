import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.users.enums import UserJobTitle


class UserReadBase(BaseModel):
    """Fields every representation of a user exposes."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="Email address, always in the @ispras.ru domain")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    job_title: UserJobTitle = Field(..., description="Job title")
    is_superuser: bool = Field(
        ..., description="Superusers may list, update and delete any account"
    )


class UserDomain(UserReadBase):
    """Service-layer user model. Carries no password."""
    username: str


class UserResponse(UserReadBase):
    """User as returned by the API."""


class UserCreate(BaseModel):
    """Registration request. Only @ispras.ru addresses are accepted;
    the username is derived from the local part of the email."""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "lebedev@ispras.ru",
                    "password": "s3cret-passphrase",
                    "first_name": "Nikita",
                    "last_name": "Lebedev",
                    "job_title": "developer",
                }
            ]
        }
    )

    email: EmailStr = Field(..., description="Email address in the @ispras.ru domain")
    password: str = Field(..., min_length=8, max_length=50,
                          description="Password, 8 to 50 characters")
    first_name: str = Field(..., min_length=2, max_length=50,
                            description="First name, 2 to 50 characters")
    last_name: str = Field(..., min_length=2, max_length=50,
                           description="Last name, 2 to 50 characters")
    job_title: UserJobTitle = Field(..., description="Job title")


class UserUpdate(BaseModel):
    """Profile update request. Only the supplied fields are changed;
    email and password are changed through their own endpoints."""
    first_name: str | None = Field(None, min_length=2, max_length=50,
                                   description="First name, 2 to 50 characters")
    last_name: str | None = Field(None, min_length=2, max_length=50,
                                  description="Last name, 2 to 50 characters")
    job_title: UserJobTitle | None = Field(None, description="Job title")


class ChangePassword(BaseModel):
    """Password change request. Allowed for the account owner only."""
    old_password: str = Field(..., min_length=8, max_length=50,
                              description="Current password")
    new_password: str = Field(..., min_length=8, max_length=50,
                              description="New password, 8 to 50 characters")


class ChangeEmail(BaseModel):
    """Email change request. Requires the current password; the username
    is re-derived from the new address."""
    password: str = Field(..., min_length=8, max_length=50,
                          description="Current password")
    new_email: EmailStr = Field(..., description="New email address in the @ispras.ru domain")
