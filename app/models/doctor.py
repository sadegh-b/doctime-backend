from sqlalchemy import Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
        index=True,
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    doctors: Mapped[list["Doctor"]] = relationship(
        "Doctor",
        back_populates="specialty_relation",
    )

    def __repr__(self) -> str:
        return f"<Specialty id={self.id} name={self.name!r}>"


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
        index=True,
    )

    medical_council_number: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
        index=True,
    )

    specialty_id: Mapped[int | None] = mapped_column(
        ForeignKey("specialties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sub_specialty: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    work_shift: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="morning",
        server_default=text("'morning'"),
    )

    province: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    city: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    address: Mapped[str | None] = mapped_column(
        String(255),
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
        String(1000),
        nullable=True,
    )

    experience_years: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    consultation_fee: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    waiting_time_estimate: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="doctor_profile",
    )

    specialty_relation: Mapped[Specialty | None] = relationship(
        "Specialty",
        back_populates="doctors",
    )

    availabilities: Mapped[list["Availability"]] = relationship(
        "Availability",
        back_populates="doctor",
        cascade="all, delete-orphan",
    )

    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="doctor",
        foreign_keys="[Appointment.doctor_id]",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Doctor id={self.id} "
            f"user_id={self.user_id} "
            f"specialty_id={self.specialty_id}>"
        )
