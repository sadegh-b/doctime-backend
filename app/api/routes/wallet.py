# backend/app/api/routes/wallet.py
import uuid
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallet", tags=["Wallet"])


# Pydantic Schemas
class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="مبلغ شارژ به تومان")
    description: Optional[str] = "شارژ کیف پول داک‌تایم"


class WalletResponse(BaseModel):
    balance: Decimal
    user_id: int
    wallet_id: int

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: int
    amount: Decimal
    transaction_type: str
    status: str
    tracking_code: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DepositResponse(BaseModel):
    success: bool
    message: str
    payment_url: str
    authority: str


class VerifyResponse(BaseModel):
    success: bool
    message: str
    amount: Decimal
    tracking_code: str


# API Endpoints
@router.get("/me", response_model=WalletResponse)
def get_my_wallet(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """دریافت اطلاعات موجودی کیف پول کاربر"""
    return WalletService.get_or_create_wallet(db=db, user_id=current_user.id)


@router.post("/deposit", response_model=DepositResponse)
def initiate_deposit(
        payload: DepositRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """گام اول: ایجاد تراکنش و تولید لینک درگاه"""
    try:
        transaction = WalletService.create_pending_deposit(
            db=db,
            user_id=current_user.id,
            amount=payload.amount,
            description=payload.description
        )

        mock_payment_url = f"https://sandbox.zarinpal.com/pg/StartPay/{transaction.tracking_code}"

        return DepositResponse(
            success=True,
            message="تراکنش با موفقیت ایجاد شد. در حال انتقال به درگاه...",
            payment_url=mock_payment_url,
            authority=transaction.tracking_code
        )
    except Exception as e:
        print(f"CRITICAL ERROR in initiate_deposit: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="سیستم بانکی موقتاً در دسترس نیست."
        )


@router.get("/verify", response_model=VerifyResponse)
def verify_payment(
        authority: str = Query(..., description="شناسه تراکنش برگشتی از بانک"),
        status_bank: str = Query(..., alias="Status", description="وضعیت ارسالی از بانک"),
        db: Session = Depends(get_db)
):
    """گام دوم: تایید نهایی تراکنش"""
    try:
        is_success = (status_bank == "OK")
        transaction = WalletService.verify_deposit(
            db=db,
            authority=authority,
            is_bank_successful=is_success
        )

        if transaction.status == "SUCCESS":
            return VerifyResponse(
                success=True,
                message="کیف پول با موفقیت شارژ شد.",
                amount=transaction.amount,
                tracking_code=transaction.tracking_code
            )

        return VerifyResponse(
            success=False,
            message="تراکنش ناموفق بود یا قبلاً پردازش شده است.",
            amount=transaction.amount,
            tracking_code=transaction.tracking_code
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        print(f"VERIFY ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="خطا در تایید تراکنش")


@router.get("/transactions", response_model=List[TransactionResponse])
def get_my_transactions(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """دریافت تاریخچه تراکنش‌ها"""
    return WalletService.get_transactions(db=db, user_id=current_user.id)
