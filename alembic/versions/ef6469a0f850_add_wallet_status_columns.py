"""add wallet status columns

Revision ID: ef6469a0f850
Revises: 2ec3a6296239
Create Date: 2026-08-15 15:37:09.567978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ef6469a0f850"
down_revision: Union[str, Sequence[str], None] = "2ec3a6296239"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "wallets",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "wallets",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("wallets", "is_locked")
    op.drop_column("wallets", "is_active")
