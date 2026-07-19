from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    # این ستون فعلاً برای سازگاری با قسمت‌های قدیمی پروژه حفظ می‌شود.
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    # nullable=True برای سازگاری با کاربران قدیمی است.
    # در schema ثبت‌نام، کد ملی برای کاربران جدید اجباری خواهد بود.
    national_id: Mapped[str | None] = mapped_column(
        String(10),
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

    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="patient",
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
