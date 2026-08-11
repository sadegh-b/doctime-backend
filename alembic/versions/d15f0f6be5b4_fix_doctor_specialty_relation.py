"""fix doctor specialty relation

Revision ID: d15f0f6be5b4
Revises: 862413c4e7d5
Create Date: 2026-07-23 16:22:03.192879

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d15f0f6be5b4"
down_revision: Union[str, Sequence[str], None] = "862413c4e7d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Deterministic approach without inspect."""

    # 1. Create specialties table
    op.create_table(
        "specialties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_specialties_id"), "specialties", ["id"], unique=False)
    op.create_index(op.f("ix_specialties_name"), "specialties", ["name"], unique=True)
    op.create_index(op.f("ix_specialties_slug"), "specialties", ["slug"], unique=True)

    # 2. Modify doctors table using batch_alter_table for SQLite compatibility
    with op.batch_alter_table("doctors", schema=None) as batch_op:
        # Add foreign key column
        batch_op.add_column(
            sa.Column("specialty_id", sa.Integer(), nullable=True)
        )

        # Create foreign key relationship
        batch_op.create_foreign_key(
            "fk_doctors_specialty_id",
            "specialties",
            ["specialty_id"],
            ["id"],
            ondelete="RESTRICT",
        )

        # Drop the old plain text specialty column
        batch_op.drop_column("specialty")


def downgrade() -> None:
    """Downgrade schema - Reverse the changes."""

    # 1. Revert doctors table changes
    with op.batch_alter_table("doctors", schema=None) as batch_op:
        # Add back the old column
        batch_op.add_column(
            sa.Column("specialty", sa.VARCHAR(length=120), nullable=True)
        )

        # Drop new foreign key and column
        batch_op.drop_constraint("fk_doctors_specialty_id", type_="foreignkey")
        batch_op.drop_column("specialty_id")

    # 2. Drop specialties table and its indexes
    op.drop_index(op.f("ix_specialties_slug"), table_name="specialties")
    op.drop_index(op.f("ix_specialties_name"), table_name="specialties")
    op.drop_index(op.f("ix_specialties_id"), table_name="specialties")
    op.drop_table("specialties")
