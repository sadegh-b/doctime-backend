"""remove appointment availability unique constraint

Revision ID: c4a8e2f17b91
Revises: 8f2c1b9a4e21
Create Date: 2026-07-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


# Revision identifiers, used by Alembic.
revision: str = "c4a8e2f17b91"
down_revision: Union[str, Sequence[str], None] = (
    "8f2c1b9a4e21"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "appointments_availability_id_key"


def upgrade() -> None:
    """Allow a cancelled appointment slot to be booked again."""

    op.drop_constraint(
        CONSTRAINT_NAME,
        "appointments",
        type_="unique",
    )


def downgrade() -> None:
    """Restore one appointment per availability constraint."""

    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "appointments",
        ["availability_id"],
    )
