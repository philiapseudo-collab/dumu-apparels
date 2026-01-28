"""Add pending_product_id to users

Revision ID: 6b7f2c1a9d2e
Revises: 9ee329fa61f5
Create Date: 2026-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b7f2c1a9d2e"
down_revision: Union[str, None] = "9ee329fa61f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pending_product_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "pending_product_id")

