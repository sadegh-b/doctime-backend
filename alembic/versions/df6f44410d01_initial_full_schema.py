"""initial_full_schema

Revision ID: df6f44410d01
Revises:
Create Date: 2026-07-20 15:33:58.523428
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision: str = "df6f44410d01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the initial database schema."""

    # ==========================
    # Users
    # ==========================

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "first_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "last_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "national_id",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "phone",
            sa.String(length=11),
            nullable=False,
        ),
        sa.Column(
            "hashed_password",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table(
        "users",
        schema=None,
    ) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_users_id"),
            ["id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_users_national_id"),
            ["national_id"],
            unique=True,
        )
        batch_op.create_index(
            batch_op.f("ix_users_phone"),
            ["phone"],
            unique=True,
        )

    # ==========================
    # Doctors
    # ==========================

    op.create_table(
        "doctors",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "medical_council_number",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "specialty",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "sub_specialty",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "work_shift",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "province",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "city",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "address",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "latitude",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "longitude",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "bio",
            sa.String(length=2000),
            nullable=True,
        ),
        sa.Column(
            "experience_years",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "consultation_fee",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "waiting_time_estimate",
            sa.String(length=100),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    with op.batch_alter_table(
        "doctors",
        schema=None,
    ) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_doctors_id"),
            ["id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f(
                "ix_doctors_medical_council_number"
            ),
            ["medical_council_number"],
            unique=True,
        )

    # ==========================
    # Availabilities
    # ==========================

    op.create_table(
        "availabilities",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "start_time",
            sa.Time(),
            nullable=False,
        ),
        sa.Column(
            "end_time",
            sa.Time(),
            nullable=False,
        ),
        sa.Column(
            "is_available",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "is_booked",
            sa.Boolean(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table(
        "availabilities",
        schema=None,
    ) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_availabilities_id"),
            ["id"],
            unique=False,
        )

    # ==========================
    # Appointments
    # ==========================

    op.create_table(
        "appointments",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "availability_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "tracking_code",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "notes",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "disclaimer",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "held_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["availability_id"],
            ["availabilities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),

        # tracking_code باید برای هر نوبت یکتا باقی بماند.
        sa.UniqueConstraint("tracking_code"),
    )

    with op.batch_alter_table(
        "appointments",
        schema=None,
    ) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_appointments_id"),
            ["id"],
            unique=False,
        )


def downgrade() -> None:
    """Remove the initial database schema."""

    # ==========================
    # Appointments
    # ==========================

    with op.batch_alter_table(
        "appointments",
        schema=None,
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_appointments_id")
        )

    op.drop_table("appointments")

    # ==========================
    # Availabilities
    # ==========================

    with op.batch_alter_table(
        "availabilities",
        schema=None,
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_availabilities_id")
        )

    op.drop_table("availabilities")

    # ==========================
    # Doctors
    # ==========================

    with op.batch_alter_table(
        "doctors",
        schema=None,
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f(
                "ix_doctors_medical_council_number"
            )
        )
        batch_op.drop_index(
            batch_op.f("ix_doctors_id")
        )

    op.drop_table("doctors")

    # ==========================
    # Users
    # ==========================

    with op.batch_alter_table(
        "users",
        schema=None,
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_users_phone")
        )
        batch_op.drop_index(
            batch_op.f("ix_users_national_id")
        )
        batch_op.drop_index(
            batch_op.f("ix_users_id")
        )

    op.drop_table("users")
