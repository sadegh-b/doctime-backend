"""add doctor wallet transaction reference uniqueness

Revision ID: 0c316c4dfc08
Revises: 532bfefdcb6d
Create Date: 2026-08-18
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0c316c4dfc08"
down_revision: Union[str, Sequence[str], None] = "532bfefdcb6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = (
    "uq_doctor_wallet_transaction_wallet_reference"
)


def upgrade() -> None:
    """
    1. پاک‌کردن جدول موقت باقی‌مانده از Migration ناموفق SQLite.
    2. اصلاح reference_idهای تکراری قدیمی بدون حذف تراکنش مالی.
    3. اضافه‌کردن Unique Constraint روی wallet_id و reference_id.
    """

    # ممکن است اجرای ناموفق قبلی این جدول موقت را باقی گذاشته باشد.
    op.execute(
        "DROP TABLE IF EXISTS "
        "_alembic_tmp_doctor_wallet_transactions"
    )

    # رکورد اول هر reference_id بدون تغییر باقی می‌ماند.
    #
    # رکوردهای تکراری بعدی به‌شکل زیر تغییر می‌کنند:
    #
    # TEST-TOPUP-001-legacy-duplicate-15
    #
    # هیچ تراکنش مالی حذف نمی‌شود و سابقه حسابداری حفظ می‌گردد.
    op.execute(
        """
        WITH ranked_transactions AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY wallet_id, reference_id
                    ORDER BY id ASC
                ) AS duplicate_number
            FROM doctor_wallet_transactions
            WHERE reference_id IS NOT NULL
              AND TRIM(reference_id) <> ''
        )
        UPDATE doctor_wallet_transactions
        SET reference_id =
            SUBSTR(reference_id, 1, 220)
            || '-legacy-duplicate-'
            || id
        WHERE id IN (
            SELECT id
            FROM ranked_transactions
            WHERE duplicate_number > 1
        )
        """
    )

    # رشته خالی از نظر Idempotency معتبر نیست.
    # آن را به NULL تبدیل می‌کنیم تا چند تراکنش قدیمی بدون شناسه
    # با Unique Constraint تداخل نداشته باشند.
    op.execute(
        """
        UPDATE doctor_wallet_transactions
        SET reference_id = NULL
        WHERE reference_id IS NOT NULL
          AND TRIM(reference_id) = ''
        """
    )

    # SQLite برای افزودن Constraint به جدول موجود به batch mode
    # نیاز دارد و جدول را به‌صورت کنترل‌شده بازسازی می‌کند.
    with op.batch_alter_table(
        "doctor_wallet_transactions",
        schema=None,
    ) as batch_op:
        batch_op.create_unique_constraint(
            CONSTRAINT_NAME,
            ["wallet_id", "reference_id"],
        )


def downgrade() -> None:
    """
    فقط Unique Constraint را حذف می‌کند.

    reference_idهای قدیمیِ اصلاح‌شده عمداً به مقدار قبلی
    برگردانده نمی‌شوند؛ چون بازگرداندن آن‌ها دوباره داده تکراری
    ایجاد می‌کند و از نظر حسابرسی مالی امن نیست.
    """

    op.execute(
        "DROP TABLE IF EXISTS "
        "_alembic_tmp_doctor_wallet_transactions"
    )

    with op.batch_alter_table(
        "doctor_wallet_transactions",
        schema=None,
    ) as batch_op:
        batch_op.drop_constraint(
            CONSTRAINT_NAME,
            type_="unique",
        )
