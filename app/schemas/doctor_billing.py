from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class SubscriptionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    price: Decimal
    duration_days: int
    description: str | None
    is_active: bool


class PromotionPackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    price: Decimal
    duration_days: int
    description: str | None
    is_active: bool


class BuySubscriptionRequest(BaseModel):
    plan_id: int
    reference_id: str | None = None


class BuyPromotionRequest(BaseModel):
    package_id: int
    reference_id: str | None = None


class DoctorSubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    plan_id: int
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    created_at: datetime


class DoctorPromotionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    package_id: int
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    created_at: datetime
