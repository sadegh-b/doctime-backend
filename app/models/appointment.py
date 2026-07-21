# app/models/appointment.py
from datetime import datetime, timezone
import random
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

def generate_tracking_code() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(10))

class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
    )

    availability_id: Mapped[int] = mapped_column(
        ForeignKey("availabilities.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",  # pending (موقت), confirmed (تایید شده/پرداخت شده), cancelled (لغو شده), completed (انجام شده)
    )

    tracking_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        default=generate_tracking_code,
    )

    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    disclaimer: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="زمان نوبت اعلام شده، برای حضور در مرکز درمانی بوده و با زمان ویزیت تفاوت دارد.",
    )

    # برای مدیریت تایم‌اوت ۱۰ دقیقه‌ای رزرو موقت
    held_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    patient = relationship(
        "User",
        back_populates="patient_appointments",
        foreign_keys=[patient_id],
    )

    doctor = relationship(
        "Doctor",
        back_populates="appointments",
        foreign_keys=[doctor_id],
    )

    availability = relationship(
        "Availability",
        back_populates="appointment",
    )
