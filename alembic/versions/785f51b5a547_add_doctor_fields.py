"""add doctor fields

Revision ID: 785f51b5a547
Revises: 6fb382133534
Create Date: 2026-07-11 22:39:05.159250
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "785f51b5a547"
down_revision: Union[str, Sequence[str], None] = "6fb382133534"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column(
            "experience_years",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "doctors",
        sa.Column(
            "consultation_fee",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("doctors", "consultation_fee")
    op.drop_column("doctors", "experience_years")
