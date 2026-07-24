# Path: backend/app/models/consultation.py

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from datetime import datetime
from ..database import Base
import enum


class ConsultationType(str, enum.Enum):
    ADDICTION = "addiction"
    CONSTIPATION = "constipation"


class ConsultationRequest(Base):
    __tablename__ = "consultation_requests"

    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String(100), nullable=True)
    phone_number = Column(String(15), nullable=False, index=True)
    consultation_type = Column(Enum(ConsultationType), nullable=False)
    summary_data = Column(Text, nullable=False)

    # کد پیگیری منحصر به فرد
    tracking_code = Column(Integer, unique=True, nullable=False, index=True)

    status = Column(String(20), default="pending")  # pending, reviewed, completed

    # سخت‌گیری مربی: استفاده از utcnow بدون پرانتز تا در هر درج (insert) مقدار جدید فراخوانی شود
    created_at = Column(DateTime, default=datetime.utcnow)
