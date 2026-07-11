# app/models/user.py
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="patient", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ارتباط یک به یک با پروفایل پزشک (اگر نقش کاربر پزشک باشد)
    # در صورت حذف کاربر، پروفایل پزشک او نیز باید به صورت خودکار حذف شود.
    doctor_profile = relationship(
        "Doctor",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ارتباط با نوبت‌های رزرو شده توسط این کاربر به عنوان بیمار
    patient_appointments = relationship(
        "Appointment",
        back_populates="patient",
        foreign_keys="[Appointment.patient_id]",
        cascade="all, delete-orphan",
    )
