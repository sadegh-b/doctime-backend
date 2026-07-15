from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    availability_id: Mapped[int] = mapped_column(
        ForeignKey("availabilities.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(30), default="booked", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    doctor = relationship("Doctor", back_populates="appointments", foreign_keys=[doctor_id])
    patient = relationship("User", back_populates="patient_appointments", foreign_keys=[patient_id])
    availability = relationship("Availability", back_populates="appointment")
