# مسیر قرارگیری فایل: backend/app/api/routes/wallet.py

from decimal import Decimal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

# استفاده از ساختار دیتابیس پروژه
from app.database import get_db

# اصلاح ایمپورت بر اساس ساختار واقعی پروژه (dependency به عنوان فایل تک)
from app.api.dependencies import get_current_user

from app.models.user import User
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallet", tags=["Wallet"])

# -----------------------------------------------------------------------------
# Pydantic Schemas (قالب‌های ورودی و خروجی داده)
# -----------------------------------------------------------------------------

class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="مبلغ شارژ به ریال/تومان")


class WalletResponse(BaseModel):
    balance: Decimal
    user_id: int
    wallet_id: int

    class Config:
        from_attributes = True  # برای سازگاری با مدل‌های SQLAlchemy در Pydantic v2


class TransactionResponse(BaseModel):
    id: int
    amount: Decimal
    transaction_type: str
    description: str | None
    created_at: datetime | str  # پذیرش هر دو فرمت تاریخ

    class Config:
        from_attributes = True


class DepositResponse(BaseModel):
    success: bool
    balance: Decimal


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@router.get("/me", response_model=WalletResponse)
def get_my_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wallet = WalletService.get_or_create_wallet(db=db, user_id=current_user.id)
    return WalletResponse(
        balance=wallet.balance,
        user_id=wallet.user_id,
        wallet_id=wallet.id,
    )


@router.get("/transactions", response_model=list[TransactionResponse])
def get_my_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transactions = WalletService.get_wallet_history(db=db, user_id=current_user.id)

    response: list[TransactionResponse] = []
    for tx in transactions:
        # استخراج مقدار متنی از Enum یا متغیر معمولی تراکنش
        tx_type_str = (
            tx.transaction_type.value
            if hasattr(tx.transaction_type, "value")
            else str(tx.transaction_type)
        )
        
        # تبدیل زمان به فرمت استاندارد ISO
        formatted_date = ""
        if tx.created_at:
            if isinstance(tx.created_at, str):
                formatted_date = tx.created_at
            else:
                formatted_date = tx.created_at.isoformat()

        response.append(
            TransactionResponse(
                id=tx.id,
                amount=tx.amount,
                transaction_type=tx_type_str,
                description=tx.description,
                created_at=formatted_date,
            )
        )
    return response


@router.post("/deposit", response_model=DepositResponse)
def deposit_wallet(
    payload: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        WalletService.deposit(
            db=db,
            user_id=current_user.id,
            amount=payload.amount,
            description="شارژ کیف پول از طریق پنل کاربری",
        )

        wallet = WalletService.get_or_create_wallet(db=db, user_id=current_user.id)
        return DepositResponse(success=True, balance=wallet.balance)

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"خطا در شارژ کیف پول: {str(e)}",
        )
