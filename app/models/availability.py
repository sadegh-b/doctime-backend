from datetime import date, time

from sqlalchemy import Boolean, Date, ForeignKey, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Availability(Base):
    __tablename__ = "availabilities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    doctor = relationship("Doctor", back_populates="availabilities")
    appointment = relationship(
        "Appointment",
        back_populates="availability",
        uselist=False,
        cascade="all, delete-orphan",
    )
