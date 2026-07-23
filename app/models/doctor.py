# app/models/doctor.py
from sqlalchemy import ForeignKey, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # نام تخصص به فارسی برای نمایش در فرانت‌اند (مثال: قلب و عروق)
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # نام انگلیسی برای آدرس‌های URL یا انتخاب آیکون‌ها (مثال: cardiology)
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # توضیحات اختیاری درباره تخصص
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # رابطه معکوس با پزشکان
    doctors = relationship(
        "Doctor",
        back_populates="specialty_relation",
    )

    def __repr__(self) -> str:
        return f"<Specialty {self.name}>"


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    medical_council_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # اصلاحیه: اضافه شدن index=True برای بهینه‌سازی جستجو بر اساس تخصص
    specialty_id: Mapped[int] = mapped_column(
        ForeignKey("specialties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # فیلد فوق‌تخصص هنوز می‌تواند به صورت متن آزاد یا اختیاری باشد
    sub_specialty: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    work_shift: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="morning",
    )

    province: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    address: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    experience_years: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    consultation_fee: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    waiting_time_estimate: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="کمتر از نیم ساعت",
    )

    # روابط (Relationships)
    user = relationship(
        "User",
        back_populates="doctor_profile",
    )

    # اتصال رابطه شی‌گرا به مدل تخصص
    specialty_relation = relationship(
        "Specialty",
        back_populates="doctors",
    )

    availabilities = relationship(
        "Availability",
        back_populates="doctor",
        cascade="all, delete-orphan",
    )

    appointments = relationship(
        "Appointment",
        back_populates="doctor",
        foreign_keys="[Appointment.doctor_id]",
        cascade="all, delete-orphan",
    )
