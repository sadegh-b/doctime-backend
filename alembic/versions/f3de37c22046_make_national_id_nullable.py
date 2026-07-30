# مسیر فایل: alembic/versions/f3de37c22046_make_national_id_nullable.py
"""make national id nullable

Revision ID: f3de37c22046
Revises: 1382244a48e0
Create Date: 2026-07-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3de37c22046'
down_revision: Union[str, None] = '1382244a48e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # استفاده از batch_alter_table برای سازگاری کامل با SQLite و PostgreSQL
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'national_id',
            existing_type=sa.String(length=10),
            nullable=True
        )


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'national_id',
            existing_type=sa.String(length=10),
            nullable=False
        )
