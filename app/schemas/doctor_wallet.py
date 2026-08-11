# app/schemas/doctor_wallet.py
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class DoctorWalletBase(BaseModel):
    balance: Decimal
    is_active: bool

class DoctorWalletRead(DoctorWalletBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    # این فیلدها را Optional می‌کنیم چون در مدل SQLAlchemy شما (DoctorWallet) وجود ندارند
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

class WalletTopUpRequest(BaseModel):
    amount: Decimal
    reference_id: Optional[str] = None
    description: Optional[str] = "Wallet top-up"

class WalletDebitRequest(BaseModel):
    amount: Decimal
    reference_id: Optional[str] = None
    description: Optional[str] = None
