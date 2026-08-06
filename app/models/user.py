# app/models/user.py

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # National ID is nullable to support users without national ID during some registration flows.
    national_id: Mapped[Optional[str]] = mapped_column(
        String(10),
        unique=True,
        index=True,
        nullable=True,
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )

    phone: Mapped[str] = mapped_column(
        String(11),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="patient",  # patient, doctor, admin
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    doctor_profile = relationship(
        "Doctor",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    patient_appointments = relationship(
        "Appointment",
        back_populates="patient",
        foreign_keys="[Appointment.patient_id]",
        cascade="all, delete-orphan",
    )

    @property
    def phone_number(self) -> str:
        """
        Compatibility property for response schemas that expect `phone_number`.

        Database/model field name:
            user.phone

        API/schema expected field name:
            user.phone_number

        This prevents FastAPI ResponseValidationError when serializing nested User objects.
        """
        return self.phone

    def __repr__(self) -> str:
        return f"<User {self.phone} - {self.role}>"
