# مسیر فایل: backend/app/models/availability.py

from datetime import date, time
from sqlalchemy import Boolean, Date, ForeignKey, Integer, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class Availability(Base):
    __tablename__ = "availabilities"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_booked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    doctor = relationship(
        "Doctor",
        back_populates="availabilities",
    )

    # تغییر نام به حالت جمع (appointments) و حذف uselist=False
    # چون هر اسلات می‌تواند تاریخچه‌ای از نوبت‌های لغوشده و نهایتاً یک نوبت فعال داشته باشد.
    appointments = relationship(
        "Appointment",
        back_populates="availability",
    )
