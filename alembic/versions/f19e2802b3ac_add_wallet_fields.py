"""add wallet fields

Revision ID: f19e2802b3ac
Revises: d83bf872b3f9
Create Date: 2026-08-10 17:14:33.085844
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision: str = "f19e2802b3ac"
down_revision: Union[str, Sequence[str], None] = "d83bf872b3f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add the currency column to the wallets table.

    The following columns already exist in the database and must not
    be added again:

    - created_at
    - updated_at
    - is_active
    """

    op.add_column(
        "wallets",
        sa.Column(
            "currency",
            sa.String(length=10),
            nullable=False,
            server_default="IRR",
        ),
    )


def downgrade() -> None:
    """
    Remove the currency column from the wallets table.
    """

    op.drop_column(
        "wallets",
        "currency",
    )
