"""remove unique constraint from appointment availability

Revision ID: 404ad212a21d
Revises: 2026_08_05_sync
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData, Table, UniqueConstraint, inspect


revision: str = "404ad212a21d"
down_revision: Union[str, None] = "2026_08_05_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "appointments"
COLUMN_NAME = "availability_id"
POSTGRES_CONSTRAINT_NAME = "appointments_availability_id_key"
MIGRATION_CONSTRAINT_NAME = "uq_appointments_availability_id"


def _get_availability_unique_constraint():
    bind = op.get_bind()
    inspector = inspect(bind)

    unique_constraints = inspector.get_unique_constraints(TABLE_NAME)

    for constraint in unique_constraints:
        column_names = constraint.get("column_names") or []

        if column_names == [COLUMN_NAME]:
            return constraint

    return None


def _remove_sqlite_unique_constraint() -> None:
    bind = op.get_bind()
    metadata = MetaData()

    appointments_table = Table(
        TABLE_NAME,
        metadata,
        autoload_with=bind,
    )

    unique_constraint_found = False

    for constraint in list(appointments_table.constraints):
        if not isinstance(constraint, UniqueConstraint):
            continue

        constrained_columns = [column.name for column in constraint.columns]

        if constrained_columns == [COLUMN_NAME]:
            appointments_table.constraints.remove(constraint)
            unique_constraint_found = True

    if not unique_constraint_found:
        return

    # SQLite cannot directly drop an anonymous UNIQUE constraint.
    # Alembic recreates the table, copies all rows and omits this constraint.
    with op.batch_alter_table(
        TABLE_NAME,
        schema=None,
        recreate="always",
        copy_from=appointments_table,
    ):
        pass


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    unique_constraint = _get_availability_unique_constraint()

    # The migration is intentionally idempotent.
    if unique_constraint is None:
        return

    if dialect_name == "sqlite":
        _remove_sqlite_unique_constraint()
        return

    constraint_name = unique_constraint.get("name")

    if not constraint_name:
        raise RuntimeError(
            "The availability_id unique constraint exists but has no name."
        )

    op.drop_constraint(
        constraint_name,
        TABLE_NAME,
        type_="unique",
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    unique_constraint = _get_availability_unique_constraint()

    if unique_constraint is not None:
        return

    constraint_name = (
        POSTGRES_CONSTRAINT_NAME
        if dialect_name == "postgresql"
        else MIGRATION_CONSTRAINT_NAME
    )

    if dialect_name == "sqlite":
        with op.batch_alter_table(
            TABLE_NAME,
            schema=None,
            recreate="always",
        ) as batch_op:
            batch_op.create_unique_constraint(
                constraint_name,
                [COLUMN_NAME],
            )
        return

    op.create_unique_constraint(
        constraint_name,
        TABLE_NAME,
        [COLUMN_NAME],
    )
