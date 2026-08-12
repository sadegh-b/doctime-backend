"""add missing doctor wallet columns

Revision ID: add_missing_doctor_wallet_columns
Revises: 5c5e209bd169
Create Date: 2026-08-12

این migration بعد از mergepoint اصلی (5c5e209bd169) اجرا می‌شود.
down_revision نباید None باشد، وگرنه Alembic دو head می‌بیند و upgrade متوقف می‌شود.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers used by Alembic.
revision: str = "add_missing_doctor_wallet_columns"
down_revision: Union[str, None] = "5c5e209bd169"  # ← head اصلی پروژه (mergepoint)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table_name: str) -> set[str]:
    """ستون‌های واقعی و فعلی جدول را برمی‌گرداند (بدون فرض قبلی)."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if table_name not in inspector.get_table_names():
        return set()

    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # ---------------------------------------------------------
    # doctor_wallets: افزودن ستون‌های گمشده
    # ---------------------------------------------------------
    if "doctor_wallets" in existing_tables:
        existing_columns = _existing_columns("doctor_wallets")

        if "currency" not in existing_columns:
            op.add_column(
                "doctor_wallets",
                sa.Column(
                    "currency",
                    sa.String(length=10),
                    nullable=False,
                    server_default=sa.text("'IRR'"),
                ),
            )

        if "is_active" not in existing_columns:
            op.add_column(
                "doctor_wallets",
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                ),
            )

        if "created_at" not in existing_columns:
            op.add_column(
                "doctor_wallets",
                sa.Column(
                    "created_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                ),
            )

        if "updated_at" not in existing_columns:
            op.add_column(
                "doctor_wallets",
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                ),
            )

        # یکتا بودن doctor_id — با inspector تازه بررسی کن، چون ستون‌ها تازه اضافه شدند
        fresh_inspector = inspect(op.get_bind())
        unique_columns = {
            tuple(c["column_names"])
            for c in fresh_inspector.get_unique_constraints("doctor_wallets")
            if c.get("column_names")
        }

        if ("doctor_id",) not in unique_columns:
            # روی SQLite فقط با batch_alter_table می‌شود constraint اضافه کرد
            with op.batch_alter_table("doctor_wallets") as batch_op:
                batch_op.create_unique_constraint(
                    "uq_doctor_wallets_doctor_id",
                    ["doctor_id"],
                )

    # ---------------------------------------------------------
    # doctor_wallet_transactions: ساخت جدول اگر وجود نداشت
    # ---------------------------------------------------------
    if "doctor_wallet_transactions" not in existing_tables:
        op.create_table(
            "doctor_wallet_transactions",
            sa.Column(
                "id",
                sa.Integer(),
                primary_key=True,
                autoincrement=True,
                nullable=False,
            ),
            sa.Column(
                "wallet_id",
                sa.Integer(),
                sa.ForeignKey("doctor_wallets.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "amount",
                sa.Numeric(12, 2),
                nullable=False,
            ),
            sa.Column(
                "transaction_type",
                sa.String(length=50),
                nullable=False,
            ),
            sa.Column(
                "reference_id",
                sa.String(length=255),
                nullable=True,
            ),
            sa.Column(
                "description",
                sa.Text(),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

        op.create_index(
            "ix_doctor_wallet_transactions_wallet_id",
            "doctor_wallet_transactions",
            ["wallet_id"],
            unique=False,
        )

        op.create_index(
            "ix_doctor_wallet_transactions_reference_id",
            "doctor_wallet_transactions",
            ["reference_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # حذف جدول transactions و ایندکس‌هایش
    if "doctor_wallet_transactions" in existing_tables:
        op.drop_index(
            "ix_doctor_wallet_transactions_reference_id",
            table_name="doctor_wallet_transactions",
        )
        op.drop_index(
            "ix_doctor_wallet_transactions_wallet_id",
            table_name="doctor_wallet_transactions",
        )
        op.drop_table("doctor_wallet_transactions")

    # حذف constraint و ستون‌ها — روی SQLite حتماً باید batch باشد
    if "doctor_wallets" in existing_tables:
        existing_columns = _existing_columns("doctor_wallets")

        with op.batch_alter_table("doctor_wallets") as batch_op:
            unique_names = {
                c.get("name")
                for c in inspect(op.get_bind()).get_unique_constraints("doctor_wallets")
                if c.get("name")
            }

            if "uq_doctor_wallets_doctor_id" in unique_names:
                batch_op.drop_constraint(
                    "uq_doctor_wallets_doctor_id",
                    type_="unique",
                )

            for column in ("updated_at", "created_at", "is_active", "currency"):
                if column in existing_columns:
                    batch_op.drop_column(column)
