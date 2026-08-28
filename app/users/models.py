import datetime
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.users.enums import UserJobTitle


class User(Base):
    """
    Model of user.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(nullable=False)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    job_title: Mapped[UserJobTitle] = mapped_column(Enum(UserJobTitle), nullable=False)
    requested_job_title: Mapped[UserJobTitle | None] = mapped_column(
        Enum(UserJobTitle), nullable=True, default=None
    )
    is_superuser: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC)
    )
    avatar_key: Mapped[str | None] = mapped_column(default=None)
    avatar_updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None
    )
    permissions: Mapped[list["UserPermission"]] = relationship(cascade="all, delete-orphan")

    def __str__(self):
        return f"User {self.username} {'(superuser)' if self.is_superuser else '(user)'}"

    def __repr__(self):
        return str(self)


class UserPermission(Base):
    """
    Model of user's permissions.
    """
    __tablename__ = "user_permissions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_permissions_user_id"),
        primary_key=True
    )
    permission: Mapped[str] = mapped_column(primary_key=True)
    granted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC)
    )
