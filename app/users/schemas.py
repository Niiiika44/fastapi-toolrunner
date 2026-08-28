import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

from app.auth.enums import Permission
from app.core.config import get_settings
from app.users.enums import UserJobTitle

settings = get_settings()


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
    requested_job_title: UserJobTitle | None = Field(
        None, description="Role the user asked for; null when there is no open request"
    )
    avatar_key: str | None = Field(None, exclude=True)
    avatar_updated_at: datetime | None = Field(None, exclude=True)

    @computed_field
    @property
    def avatar_url(self) -> str | None:
        if not self.avatar_key:
            return None
        version = (
            int(self.avatar_updated_at.timestamp() * 1_000_000)
            if self.avatar_updated_at
            else 0
        )
        return f"{settings.API_PREFIX}/users/{self.id}/avatar?v={version}"


class UserDomain(UserReadBase):
    """Service-layer user model. Carries no password."""
    username: str


class UserResponse(UserReadBase):
    """User as returned by the API."""


class CurrentUserResponse(UserResponse):
    """The signed-in account, with the permissions the server will actually honour."""
    permissions: list[Permission] = Field(
        default_factory=list,
        validation_alias="__effective_permissions__",
        description="Effective permissions: the role baseline plus individual grants",
    )


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
    model_config = ConfigDict(extra="forbid")
    first_name: str | None = Field(None, min_length=2, max_length=50,
                                   description="First name, 2 to 50 characters")
    last_name: str | None = Field(None, min_length=2, max_length=50,
                                  description="Last name, 2 to 50 characters")


class RoleAssignment(BaseModel):
    """Direct role assignment by an admin."""
    job_title: UserJobTitle = Field(..., description="Role to assign")


class RoleRequest(BaseModel):
    """Request to change the current role of the user."""
    job_title: UserJobTitle = Field(..., description="Role to request to assign")


class RoleApproval(BaseModel):
    """Role approval by an admin."""
    expected_job_title: UserJobTitle = Field(..., description="Role to approve")


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


class UserPermissionBase(BaseModel):
    """One individual permission granted to a user on top of the role baseline."""
    model_config = ConfigDict(from_attributes=True)

    permission: str = Field(..., description=("Permission name"), examples=["test:upload"])
    granted_at: datetime = Field(..., description="When the permission was granted")


class UserPermissionDomain(UserPermissionBase):
    """Service-layer grant model."""


class UserPermissionResponse(UserPermissionDomain):
    """Grant as returned by the API."""


class AvatarLinkDomain(BaseModel):
    """Avatar handed over as a link to the storage."""
    model_config = ConfigDict(frozen=True)

    url: str = Field(..., description="Presigned url")


class AvatarContentDomain(BaseModel):
    """Avatar handed over as bytes, for backends that cannot sign links."""
    model_config = ConfigDict(frozen=True)

    content: bytes = Field(..., description="Image content")
