"""add consultation requests table

Revision ID: 1382244a48e0
Revises: bdd30460bf8a
Create Date: 2026-07-24 16:07:37.537092
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# Revision identifiers, used by Alembic.
revision: str = "1382244a48e0"
down_revision: Union[str, Sequence[str], None] = "bdd30460bf8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "consultation_requests"
ENUM_NAME = "consultationtype"

INDEX_ID = "ix_consultation_requests_id"
INDEX_PHONE_NUMBER = "ix_consultation_requests_phone_number"
INDEX_TRACKING_CODE = "ix_consultation_requests_tracking_code"


def upgrade() -> None:
    """Create the consultation requests table and indexes safely."""

    bind = op.get_bind()
    inspector = inspect(bind)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'consultationtype'
            ) THEN
                CREATE TYPE consultationtype AS ENUM (
                    'ADDICTION',
                    'CONSTIPATION'
                );
            END IF;
        END
        $$;
        """
    )

    existing_tables = set(inspector.get_table_names())

    if TABLE_NAME not in existing_tables:
        consultation_type = postgresql.ENUM(
            "ADDICTION",
            "CONSTIPATION",
            name=ENUM_NAME,
            create_type=False,
        )

        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("patient_name", sa.String(length=100), nullable=True),
            sa.Column("phone_number", sa.String(length=15), nullable=False),
            sa.Column(
                "consultation_type",
                consultation_type,
                nullable=False,
            ),
            sa.Column("summary_data", sa.Text(), nullable=False),
            sa.Column("tracking_code", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {
        index["name"]
        for index in inspect(bind).get_indexes(TABLE_NAME)
        if index.get("name")
    }

    if INDEX_ID not in existing_indexes:
        op.create_index(
            INDEX_ID,
            TABLE_NAME,
            ["id"],
            unique=False,
        )

    if INDEX_PHONE_NUMBER not in existing_indexes:
        op.create_index(
            INDEX_PHONE_NUMBER,
            TABLE_NAME,
            ["phone_number"],
            unique=False,
        )

    if INDEX_TRACKING_CODE not in existing_indexes:
        op.create_index(
            INDEX_TRACKING_CODE,
            TABLE_NAME,
            ["tracking_code"],
            unique=True,
        )


def downgrade() -> None:
    """Drop the consultation requests table safely."""

    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = set(inspector.get_table_names())

    if TABLE_NAME not in existing_tables:
        return

    existing_indexes = {
        index["name"]
        for index in inspect(bind).get_indexes(TABLE_NAME)
        if index.get("name")
    }

    if INDEX_TRACKING_CODE in existing_indexes:
        op.drop_index(
            INDEX_TRACKING_CODE,
            table_name=TABLE_NAME,
        )

    if INDEX_PHONE_NUMBER in existing_indexes:
        op.drop_index(
            INDEX_PHONE_NUMBER,
            table_name=TABLE_NAME,
        )

    if INDEX_ID in existing_indexes:
        op.drop_index(
            INDEX_ID,
            table_name=TABLE_NAME,
        )

    op.drop_table(TABLE_NAME)
