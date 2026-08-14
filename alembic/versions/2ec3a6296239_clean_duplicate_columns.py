"""clean duplicate columns

Revision ID: 2ec3a6296239
Revises: 1eaf24a6e725
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2ec3a6296239"
down_revision: Union[str, Sequence[str], None] = "1eaf24a6e725"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "doctor_wallets"
CONSTRAINT_NAME = "uq_doctor_wallets_doctor_id"


def _table_exists(table_name: str) -> bool:
    """Check whether a table exists in the current database."""
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(table_name)


def _get_unique_constraint_names(table_name: str) -> set[str]:
    """Return the named unique constraints of a table."""
    inspector = sa.inspect(op.get_bind())

    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def _get_column_names(table_name: str) -> set[str]:
    """Return the column names of a table."""
    inspector = sa.inspect(op.get_bind())

    return {
        column["name"]
        for column in inspector.get_columns(table_name)
    }


def upgrade() -> None:
    """Remove the duplicate doctor_id unique constraint when it exists."""

    # Some valid database schemas do not contain doctor_wallets.
    # In that case this migration has nothing to change.
    if not _table_exists(TABLE_NAME):
        return

    unique_constraints = _get_unique_constraint_names(TABLE_NAME)

    if CONSTRAINT_NAME not in unique_constraints:
        return

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.drop_constraint(
            CONSTRAINT_NAME,
            type_="unique",
        )


def downgrade() -> None:
    """Restore the doctor_id unique constraint when possible."""

    if not _table_exists(TABLE_NAME):
        return

    columns = _get_column_names(TABLE_NAME)

    if "doctor_id" not in columns:
        return

    unique_constraints = _get_unique_constraint_names(TABLE_NAME)

    if CONSTRAINT_NAME in unique_constraints:
        return

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.create_unique_constraint(
            CONSTRAINT_NAME,
            ["doctor_id"],
        )
