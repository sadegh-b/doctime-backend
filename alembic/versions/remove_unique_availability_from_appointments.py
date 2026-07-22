"""remove unique availability from appointments

Revision ID: c4a8e2f17b91
Revises: 8f2c1b9a4e21
Create Date: 2026-07-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c4a8e2f17b91"
down_revision: Union[str, Sequence[str], None] = "8f2c1b9a4e21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow rebooking a cancelled appointment slot."""
    op.drop_constraint(
        "appointments_availability_id_key",
        "appointments",
        type_="unique",
    )


def downgrade() -> None:
    """Restore the old unique constraint."""
    op.create_unique_constraint(
        "appointments_availability_id_key",
        "appointments",
        ["availability_id"],
    )
