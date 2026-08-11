"""sync doctor wallet tables with updated models

Revision ID: sync_doctor_wallet_columns
Revises: d83bf872b3f9
Create Date: 2026-08-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "sync_doctor_wallet_columns"
down_revision = "d83bf872b3f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    # doctor_wallets
    if inspector.has_table("doctor_wallets"):
        wallet_cols = {c["name"] for c in inspector.get_columns("doctor_wallets")}

        if "is_active" not in wallet_cols:
            op.add_column(
                "doctor_wallets",
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("1"),
                ),
            )

        if "currency" not in wallet_cols:
            op.add_column(
                "doctor_wallets",
                sa.Column(
                    "currency",
                    sa.String(length=10),
                    nullable=False,
                    server_default="IRR",
                ),
            )

        if "created_at" not in wallet_cols:
            op.add_column(
                "doctor_wallets",
                sa.Column(
                    "created_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                ),
            )

        if "updated_at" not in wallet_cols:
            op.add_column(
                "doctor_wallets",
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                ),
            )

    # doctor_wallet_transactions
    if inspector.has_table("doctor_wallet_transactions"):
        tx_cols = {c["name"] for c in inspector.get_columns("doctor_wallet_transactions")}

        if "created_at" not in tx_cols:
            op.add_column(
                "doctor_wallet_transactions",
                sa.Column(
                    "created_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                ),
            )


def downgrade() -> None:
    # SQLite-safe downgrade is intentionally omitted for this sync migration.
    pass
