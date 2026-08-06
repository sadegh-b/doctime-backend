# Path: alembic/versions/404ad212a21d_remove_unique_constraint_from_.py

"""remove unique constraint from availability id

Revision ID: 404ad212a21d
Revises: 2026_08_05_sync
Create Date: 2026-08-06 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '404ad212a21d'
down_revision: Union[str, None] = '2026_08_05_sync'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # بازسازی جدول بدون نیاز به پاس دادن نام قید غیرموجود.
    # المبیک با اجرای pass در بدنه batch_alter_table، جدول را بر اساس ساختار مدل‌های جدید (بدون unique) مجدداً می‌سازد.
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        pass


def downgrade() -> None:
    # در صورت برگشت مایگریشن، قید یکتایی را دوباره به ستون اضافه می‌کنیم.
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_appointments_availability_id', ['availability_id'])
