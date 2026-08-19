# Path: app/schemas/doctor_wallet.py

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# =========================================================
# Base & Read Schemas (کیف پول و تراکنش‌ها)
# =========================================================

class DoctorWalletBase(BaseModel):
    balance: Decimal
    is_active: bool


class DoctorWalletRead(DoctorWalletBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    currency: Optional[str] = "IRR"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DoctorWalletTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wallet_id: int
    transaction_type: str
    amount: Decimal
    description: Optional[str] = None
    reference_id: Optional[str] = None
    created_at: datetime


# =========================================================
# Operational Request Schemas (درخواست‌های عملیاتی)
# =========================================================

class WalletTopUpRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="مبلغ شارژ باید بیشتر از صفر باشد")
    reference_id: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = "Wallet top-up"


class WalletDebitRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="مبلغ کسر باید بیشتر از صفر باشد")
    transaction_type: str = Field(default="debit", max_length=50)
    reference_id: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class BuySubscriptionRequest(BaseModel):
    plan_id: int = Field(..., description="شناسه پلن اشتراک مورد نظر")
    reference_id: Optional[str] = None


class BuyPromotionRequest(BaseModel):
    package_id: int = Field(..., description="شناسه پکیج پروموشن مورد نظر")
    reference_id: Optional[str] = None


# =========================================================
# Payment Gateway Schemas (درخواست و پاسخ درگاه پرداخت)
# =========================================================

class PaymentInitRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="مبلغ شارژ به ریال")


class PaymentInitResponse(BaseModel):
    payment_id: int
    authority: str
    payment_url: str


# =========================================================
# Operational Response Schemas (مدل‌های خروجی عملیات‌ها)
# =========================================================

class WalletOperationResponse(BaseModel):
    wallet: DoctorWalletRead
    transaction: DoctorWalletTransactionRead
    message: str


class SubscriptionOperationResponse(BaseModel):
    wallet: DoctorWalletRead
    transaction: DoctorWalletTransactionRead
    subscription_id: int
    starts_at: datetime
    ends_at: datetime
    message: str


class PromotionOperationResponse(BaseModel):
    wallet: DoctorWalletRead
    transaction: DoctorWalletTransactionRead
    promotion_id: int
    starts_at: datetime
    ends_at: datetime
    message: str
