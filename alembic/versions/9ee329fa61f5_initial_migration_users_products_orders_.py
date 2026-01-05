"""Initial migration: users, products, orders, conversation_logs

Revision ID: 9ee329fa61f5
Revises: 
Create Date: 2026-01-04 14:20:32.717819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ee329fa61f5'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
