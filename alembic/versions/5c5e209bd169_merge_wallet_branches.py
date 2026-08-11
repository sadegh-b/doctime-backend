"""merge wallet branches

Revision ID: 5c5e209bd169
Revises: f19e2802b3ac, sync_doctor_wallet_columns
Create Date: 2026-08-11 15:52:27.309413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c5e209bd169'
down_revision: Union[str, Sequence[str], None] = ('f19e2802b3ac', 'sync_doctor_wallet_columns')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
