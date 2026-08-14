from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.wallet import TransactionStatus
from app.services.wallet_service import WalletService
from app.services.payments import get_payment_gateway

router = APIRouter(prefix="/wallet", tags=["Wallet"])


class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="مبلغ شارژ به تومان")
    description: Optional[str] = "شارژ کیف پول داک‌تایم"


class WalletResponse(BaseModel):
    balance: Decimal
    user_id: int
    wallet_id: int


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


@router.get("/me", response_model=WalletResponse)
def get_my_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wallet = WalletService.get_or_create_wallet(
        db=db,
        user_id=current_user.id,
    )

    return WalletResponse(
        wallet_id=wallet.id,
        user_id=wallet.user_id,
        balance=wallet.balance,
    )


@router.post("/deposit", response_model=DepositResponse)
def initiate_deposit(
    payload: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = None

    try:
        transaction = WalletService.create_pending_deposit(
            db=db,
            user_id=current_user.id,
            amount=payload.amount,
            description=payload.description,
        )

        gateway = get_payment_gateway()

        # در ساختار فعلی سیستم، verify_deposit با authority ورودی
        # روی Transaction.tracking_code جست‌وجو می‌کند.
        # بنابراین authority واقعی بانک را بعد از پاسخ بانک
        # داخل tracking_code ذخیره می‌کنیم.
        callback_url = (
            f"{settings.PAYMENT_CALLBACK_BASE_URL}/wallet/verify"
            f"?authority={transaction.tracking_code}"
            f"&Status=OK"
        )

        payment_result = gateway.create_payment(
            amount=int(transaction.amount),
            order_id=str(transaction.id),
            callback_url=callback_url,
            additional_data=payload.description or "",
            payer_id=str(current_user.id),
        )

        transaction.tracking_code = payment_result.authority
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        return DepositResponse(
            success=True,
            message="تراکنش با موفقیت ایجاد شد. در حال انتقال به درگاه...",
            payment_url=payment_result.payment_url,
            authority=payment_result.authority,
        )

    except HTTPException as exc:
        if transaction is not None:
            try:
                transaction.status = TransactionStatus.FAILED
                db.add(transaction)
                db.commit()
            except Exception:
                db.rollback()
        raise exc

    except Exception as exc:
        if transaction is not None:
            try:
                transaction.status = TransactionStatus.FAILED
                db.add(transaction)
                db.commit()
            except Exception:
                db.rollback()

        print(
            f"CRITICAL ERROR in initiate_deposit | "
            f"user_id={current_user.id} | amount={payload.amount} | error={exc}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="سیستم بانکی موقتاً در دسترس نیست.",
        ) from exc


@router.get("/verify", response_model=VerifyResponse)
def verify_payment(
    authority: str = Query(..., description="شناسه تراکنش برگشتی از بانک"),
    status_bank: str = Query(
        ...,
        alias="Status",
        description="وضعیت ارسالی از بانک",
    ),
    db: Session = Depends(get_db),
):
    try:
        normalized_status = status_bank.strip().upper()
        is_success = normalized_status == "OK"

        transaction = WalletService.verify_deposit(
            db=db,
            authority=authority,
            is_bank_successful=is_success,
        )

        if transaction.status == TransactionStatus.SUCCESS:
            return VerifyResponse(
                success=True,
                message="کیف پول با موفقیت شارژ شد.",
                amount=transaction.amount,
                tracking_code=transaction.tracking_code,
            )

        return VerifyResponse(
            success=False,
            message="تراکنش ناموفق بود یا قبلاً پردازش شده است.",
            amount=transaction.amount,
            tracking_code=transaction.tracking_code,
        )

    except HTTPException:
        raise

    except Exception as exc:
        print(
            f"VERIFY ERROR | authority={authority} | "
            f"Status={status_bank} | error={exc}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای داخلی هنگام تایید تراکنش",
        ) from exc


@router.get("/transactions", response_model=List[TransactionResponse])
def get_my_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return WalletService.get_wallet_history(
        db=db,
        user_id=current_user.id,
    )
