"""add PROCESSING to teststatus enum

Revision ID: a06a411f81fe
Revises: c3b5a7078096
Create Date: 2026-06-30 19:53:30.798404

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a06a411f81fe'
down_revision: Union[str, Sequence[str], None] = 'c3b5a7078096'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE teststatus ADD VALUE IF NOT EXISTS 'PROCESSING' BEFORE 'PARSED'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
