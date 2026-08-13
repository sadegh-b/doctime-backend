"""add wallet status and created_at columns

Revision ID: 1eaf24a6e725
Revises: add_missing_doctor_wallet_columns
Create Date: 2026-08-13 13:25:46.490009

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1eaf24a6e725'
down_revision: Union[str, Sequence[str], None] = 'add_missing_doctor_wallet_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "wallets",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "wallets",
        sa.Column(
            "is_locked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "wallets",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("wallets", "created_at")
    op.drop_column("wallets", "is_locked")
    op.drop_column("wallets", "is_active")
