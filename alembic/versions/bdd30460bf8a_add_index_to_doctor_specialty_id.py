"""add index to doctor specialty_id

Revision ID: bdd30460bf8a
Revises: d15f0f6be5b4
Create Date: 2026-07-23 16:28:42.331557
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


# Revision identifiers, used by Alembic.
revision: str = "bdd30460bf8a"
down_revision: Union[str, Sequence[str], None] = "d15f0f6be5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "doctors"
COLUMN_NAME = "specialty_id"
INDEX_NAME = "ix_doctors_specialty_id"


def upgrade() -> None:
    """Create the specialty_id index only when it does not already exist."""

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = set(inspector.get_table_names())

    if TABLE_NAME not in existing_tables:
        raise RuntimeError(
            f"Cannot create index {INDEX_NAME!r}: "
            f"table {TABLE_NAME!r} does not exist."
        )

    existing_columns = {
        column["name"]
        for column in inspector.get_columns(TABLE_NAME)
    }

    if COLUMN_NAME not in existing_columns:
        raise RuntimeError(
            f"Cannot create index {INDEX_NAME!r}: "
            f"column {TABLE_NAME}.{COLUMN_NAME} does not exist."
        )

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes(TABLE_NAME)
        if index.get("name")
    }

    if INDEX_NAME in existing_indexes:
        return

    op.create_index(
        INDEX_NAME,
        TABLE_NAME,
        [COLUMN_NAME],
        unique=False,
    )


def downgrade() -> None:
    """Drop the specialty_id index only when it exists."""

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = set(inspector.get_table_names())

    if TABLE_NAME not in existing_tables:
        return

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes(TABLE_NAME)
        if index.get("name")
    }

    if INDEX_NAME not in existing_indexes:
        return

    op.drop_index(
        INDEX_NAME,
        table_name=TABLE_NAME,
    )
