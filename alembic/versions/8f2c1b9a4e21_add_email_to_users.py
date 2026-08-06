"""add_email_to_users

Revision ID: 8f2c1b9a4e21
Revises: df6f44410d01
Create Date: 2026-07-21 13:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# Revision identifiers, used by Alembic.
revision: str = "8f2c1b9a4e21"
down_revision: Union[str, Sequence[str], None] = "df6f44410d01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EMAIL_COLUMN_NAME = "email"
EMAIL_INDEX_NAME = "ix_users_email"


def upgrade() -> None:
    """Add the users.email column and its unique index if missing."""

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes("users")
    }

    needs_email_column = EMAIL_COLUMN_NAME not in existing_columns
    needs_email_index = EMAIL_INDEX_NAME not in existing_indexes

    if not needs_email_column and not needs_email_index:
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if needs_email_column:
            batch_op.add_column(
                sa.Column(
                    EMAIL_COLUMN_NAME,
                    sa.String(length=255),
                    nullable=True,
                )
            )

        if needs_email_index:
            batch_op.create_index(
                EMAIL_INDEX_NAME,
                [EMAIL_COLUMN_NAME],
                unique=True,
            )


def downgrade() -> None:
    """Remove the users.email unique index and column if they exist."""

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes("users")
    }

    if (
        EMAIL_COLUMN_NAME not in existing_columns
        and EMAIL_INDEX_NAME not in existing_indexes
    ):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if EMAIL_INDEX_NAME in existing_indexes:
            batch_op.drop_index(EMAIL_INDEX_NAME)

        if EMAIL_COLUMN_NAME in existing_columns:
            batch_op.drop_column(EMAIL_COLUMN_NAME)
