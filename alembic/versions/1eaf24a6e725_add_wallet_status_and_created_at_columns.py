"""add wallet status and created_at columns

Revision ID: 1eaf24a6e725
Revises: add_missing_doctor_wallet_columns
Create Date: 2026-08-13 13:25:46.490009

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1eaf24a6e725"
down_revision: Union[str, Sequence[str], None] = (
    "add_missing_doctor_wallet_columns"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_existing_columns(table_name: str) -> set[str]:
    """Return the existing column names for a database table."""
    inspector = sa.inspect(op.get_bind())

    return {
        column["name"]
        for column in inspector.get_columns(table_name)
    }


def upgrade() -> None:
    """Add missing wallet columns without duplicating existing columns."""
    existing_columns = _get_existing_columns("wallets")

    if "is_active" not in existing_columns:
        op.add_column(
            "wallets",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )

    if "is_locked" not in existing_columns:
        op.add_column(
            "wallets",
            sa.Column(
                "is_locked",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    if "created_at" not in existing_columns:
        op.add_column(
            "wallets",
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True,
            ),
        )


def downgrade() -> None:
    """Remove wallet columns when they exist."""
    existing_columns = _get_existing_columns("wallets")

    if "created_at" in existing_columns:
        op.drop_column("wallets", "created_at")

    if "is_locked" in existing_columns:
        op.drop_column("wallets", "is_locked")

    if "is_active" in existing_columns:
        op.drop_column("wallets", "is_active")
