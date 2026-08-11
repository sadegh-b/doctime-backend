"""add_email_to_users

Revision ID: 8f2c1b9a4e21
Revises: df6f44410d01
Create Date: 2026-07-21 13:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision: str = "8f2c1b9a4e21"
down_revision: Union[str, Sequence[str], None] = "df6f44410d01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the users.email column and its unique index."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "email",
                sa.String(length=255),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_users_email",
            ["email"],
            unique=True,
        )


def downgrade() -> None:
    """Remove the users.email unique index and column."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_email")
        batch_op.drop_column("email")
