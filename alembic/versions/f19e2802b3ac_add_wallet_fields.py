"""add wallet fields

Revision ID: f19e2802b3ac
Revises: d83bf872b3f9
Create Date: 2026-08-10 17:14:33.085844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f19e2802b3ac'
down_revision: Union[str, Sequence[str], None] = 'd83bf872b3f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('doctor_wallets', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'currency',
                sa.String(length=10),
                nullable=False,
                server_default=sa.text("'IRR'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                'created_at',
                sa.DateTime(),
                nullable=False,
                server_default=sa.text('(CURRENT_TIMESTAMP)'),
            )
        )
        batch_op.add_column(
            sa.Column(
                'updated_at',
                sa.DateTime(),
                nullable=False,
                server_default=sa.text('(CURRENT_TIMESTAMP)'),
            )
        )

    # اختیاری: اگر نمی‌خواهی defaultها بعد از migration روی ستون بمانند،
    # باید در SQLite معمولاً با alter ساده نمی‌شود و نیاز به batch جداگانه دارد.
    # فعلاً نگه‌داشتن server_default مشکلی ایجاد نمی‌کند.


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('doctor_wallets', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('currency')
