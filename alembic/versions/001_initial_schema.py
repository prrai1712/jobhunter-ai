"""Initial schema setup.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-06-11 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # We will let the programmatic fallback Base.metadata.create_all initialize the tables,
    # or Alembic can run this as a placeholder.
    pass


def downgrade() -> None:
    pass
