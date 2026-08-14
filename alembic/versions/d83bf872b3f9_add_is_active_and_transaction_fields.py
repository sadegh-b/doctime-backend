"""add is_active and transaction fields

Revision ID: d83bf872b3f9
Revises: 84dadbaf28ac
Create Date: 2026-08-10 16:44:24.359704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd83bf872b3f9'
down_revision: Union[str, Sequence[str], None] = '84dadbaf28ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_existing_columns(table_name: str) -> set[str]:
    """Return the existing column names for a database table."""
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    existing_columns = _get_existing_columns('wallets')

    if 'is_active' not in existing_columns:
        with op.batch_alter_table('wallets', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    'is_active',
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                )
            )


def downgrade() -> None:
    """Downgrade schema."""
    existing_columns = _get_existing_columns('wallets')

    if 'is_active' in existing_columns:
        with op.batch_alter_table('wallets', schema=None) as batch_op:
            batch_op.drop_column('is_active')
