from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database.base import Base


class DoctorPayment(Base):
    __tablename__ = "doctor_payments"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    gateway = Column(String(50), nullable=False, default="mellat")
    authority = Column(String(255), nullable=True, index=True)
    sale_reference_id = Column(String(255), nullable=True, unique=True, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, paid, failed
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    doctor = relationship("Doctor", backref="payments")
