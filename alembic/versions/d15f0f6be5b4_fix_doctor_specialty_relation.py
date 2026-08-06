"""fix doctor specialty relation

Revision ID: d15f0f6be5b4
Revises: 862413c4e7d5
Create Date: 2026-07-23 16:22:03.192879

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "d15f0f6be5b4"
down_revision: Union[str, Sequence[str], None] = "862413c4e7d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    # ۱. بررسی وجود جدول specialties
    existing_tables = inspector.get_table_names()
    has_specialties = "specialties" in existing_tables

    if not has_specialties:
        op.create_table(
            "specialties",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("slug", sa.String(length=100), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    # ۲. مدیریت ایندکس‌های جدول specialties
    if "specialties" in existing_tables or not has_specialties:
        existing_indexes = {
            index["name"] for index in inspector.get_indexes("specialties")
        }

        with op.batch_alter_table("specialties", schema=None) as batch_op:
            if "ix_specialties_id" not in existing_indexes:
                batch_op.create_index(
                    batch_op.f("ix_specialties_id"), ["id"], unique=False
                )
            if "ix_specialties_name" not in existing_indexes:
                batch_op.create_index(
                    batch_op.f("ix_specialties_name"), ["name"], unique=True
                )
            if "ix_specialties_slug" not in existing_indexes:
                batch_op.create_index(
                    batch_op.f("ix_specialties_slug"), ["slug"], unique=True
                )

    # ۳. مدیریت جدول doctors
    if "doctors" in existing_tables:
        doctor_columns = {
            column["name"] for column in inspector.get_columns("doctors")
        }
        doctor_fks = {
            fk["name"] for fk in inspector.get_foreign_keys("doctors")
        }

        with op.batch_alter_table("doctors", schema=None) as batch_op:
            # اضافه کردن specialty_id در صورت عدم وجود
            if "specialty_id" not in doctor_columns:
                # موقتا nullable=True می‌گذاریم تا دیتای قبلی خطا ندهد، بعد از ریلیشن آن را تغییر می‌دهیم
                batch_op.add_column(
                    sa.Column("specialty_id", sa.Integer(), nullable=True)
                )

            # اضافه کردن کلید خارجی در صورت عدم وجود
            if "fk_doctors_specialty_id" not in doctor_fks:
                batch_op.create_foreign_key(
                    "fk_doctors_specialty_id",
                    "specialties",
                    ["specialty_id"],
                    ["id"],
                    ondelete="RESTRICT",
                )

            # حذف ستون قدیمی specialty در صورت وجود
            if "specialty" in doctor_columns:
                batch_op.drop_column("specialty")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "doctors" in existing_tables:
        doctor_columns = {
            column["name"] for column in inspector.get_columns("doctors")
        }
        doctor_fks = {
            fk["name"] for fk in inspector.get_foreign_keys("doctors")
        }

        with op.batch_alter_table("doctors", schema=None) as batch_op:
            if "specialty" not in doctor_columns:
                batch_op.add_column(
                    sa.Column(
                        "specialty", sa.VARCHAR(length=120), nullable=True
                    )
                )

            if "fk_doctors_specialty_id" in doctor_fks:
                batch_op.drop_constraint(
                    "fk_doctors_specialty_id", type_="foreignkey"
                )

            if "specialty_id" in doctor_columns:
                batch_op.drop_column("specialty_id")

    if "specialties" in existing_tables:
        existing_indexes = {
            index["name"] for index in inspector.get_indexes("specialties")
        }

        with op.batch_alter_table("specialties", schema=None) as batch_op:
            if "ix_specialties_slug" in existing_indexes:
                batch_op.drop_index(batch_op.f("ix_specialties_slug"))
            if "ix_specialties_name" in existing_indexes:
                batch_op.drop_index(batch_op.f("ix_specialties_name"))
            if "ix_specialties_id" in existing_indexes:
                batch_op.drop_index(batch_op.f("ix_specialties_id"))

        op.drop_table("specialties")
