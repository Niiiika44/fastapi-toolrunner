import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


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
    job_title: Mapped[str] = mapped_column(nullable=False)
    is_superuser: Mapped[bool] = mapped_column(nullable=False, default=False)

    def __str__(self):
        return f"User {self.username} {'(superuser)' if self.is_superuser else '(user)'}"

    def __repr__(self):
        return str(self)
