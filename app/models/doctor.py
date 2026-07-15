from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    specialty: Mapped[str] = mapped_column(String(120), nullable=False)
    work_shift: Mapped[str] = mapped_column(String(20), nullable=False, default="morning")
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    experience_years: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consultation_fee: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="doctor_profile")
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
