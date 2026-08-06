"""force drop appointments availability unique constraint

Revision ID: 2026_08_06_force_drop_availability_unique
Revises: 404ad212a21d
"""

from typing import Sequence, Union

from alembic import op


revision: str = "2026_08_06_force_drop_availability_unique"
down_revision: Union[str, None] = "404ad212a21d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute(
            """
            ALTER TABLE appointments
            DROP CONSTRAINT IF EXISTS appointments_availability_id_key
            """
        )
        return

    # SQLite local database was already fixed by the previous migration.
    # Keep this migration idempotent and safe for local development.
    if dialect_name == "sqlite":
        return

    raise RuntimeError(
        f"Unsupported database dialect for this migration: {dialect_name}"
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute(
            """
            ALTER TABLE appointments
            ADD CONSTRAINT appointments_availability_id_key
            UNIQUE (availability_id)
            """
        )
        return

    if dialect_name == "sqlite":
        return

    raise RuntimeError(
        f"Unsupported database dialect for this migration: {dialect_name}"
    )
