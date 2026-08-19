from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.database.base import Base

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    price = Column(Numeric(12, 2), nullable=False, default=0)
    duration_days = Column(Integer, nullable=False, default=30)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    doctor_subscriptions = relationship("DoctorSubscription", back_populates="plan")


class DoctorSubscription(Base):
    __tablename__ = "doctor_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False)
    starts_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # روابط برای دسترسی آسان‌تر
    plan = relationship("SubscriptionPlan", back_populates="doctor_subscriptions")
    # doctor = relationship("Doctor", back_populates="subscriptions") # فرض بر اینکه در مدل Doctor تعریف شده


class PromotionPackage(Base):
    __tablename__ = "promotion_packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    price = Column(Numeric(12, 2), nullable=False, default=0)
    duration_days = Column(Integer, nullable=False, default=7)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    doctor_promotions = relationship("DoctorPromotion", back_populates="package")


class DoctorPromotion(Base):
    __tablename__ = "doctor_promotions"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    package_id = Column(Integer, ForeignKey("promotion_packages.id", ondelete="RESTRICT"), nullable=False)
    starts_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # رابطه کامل
    package = relationship("PromotionPackage", back_populates="doctor_promotions")
