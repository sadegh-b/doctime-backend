# Path: app/api/routes/doctor_wallet.py

from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_doctor, get_db
from app.core.config import settings
from app.models.doctor import Doctor
from app.models.doctor_payment import DoctorPayment
from app.schemas.doctor_wallet import (
    BuyPromotionRequest,
    BuySubscriptionRequest,
    DoctorWalletRead,
    DoctorWalletTransactionRead,
    PaymentInitRequest,
    PaymentInitResponse,
    PromotionOperationResponse,
    SubscriptionOperationResponse,
    WalletDebitRequest,
    WalletOperationResponse,
    WalletTopUpRequest,
)
from app.services.doctor_wallet_service import DoctorWalletService
from app.services.payments.mellat import MellatPaymentGateway

router = APIRouter(prefix="/doctor-wallet", tags=["Doctor Wallet"])


# =========================================================
# Wallet Info & Transactions
# =========================================================

@router.get("", response_model=DoctorWalletRead)
def get_my_wallet(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """دریافت اطلاعات و موجودی کیف پول پزشک جاری"""
    wallet = DoctorWalletService.get_or_create_wallet(db, doctor_id=current_doctor.id)
    return wallet


@router.get("/transactions", response_model=List[DoctorWalletTransactionRead])
def get_my_transactions(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """دریافت لیست تمامی تراکنش‌های کیف پول پزشک جاری"""
    return DoctorWalletService.get_transactions(db, doctor_id=current_doctor.id)


# =========================================================
# Manual Balance Operations (Top-up & Debit)
# =========================================================

@router.post("/topup", response_model=WalletOperationResponse)
def top_up_wallet(
    payload: WalletTopUpRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """شارژ مستقیم موجودی کیف پول"""
    wallet, transaction = DoctorWalletService.top_up(
        db=db,
        doctor_id=current_doctor.id,
        amount=payload.amount,
        reference_id=payload.reference_id,
        description=payload.description or "شارژ کیف پول",
    )
    return {
        "wallet": wallet,
        "transaction": transaction,
        "message": "کیف پول با موفقیت شارژ شد",
    }


@router.post("/debit", response_model=WalletOperationResponse)
def debit_wallet(
    payload: WalletDebitRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """کسر از موجودی کیف پول"""
    wallet, transaction = DoctorWalletService.debit(
        db=db,
        doctor_id=current_doctor.id,
        amount=payload.amount,
        transaction_type=payload.transaction_type,
        reference_id=payload.reference_id,
        description=payload.description,
    )
    return {
        "wallet": wallet,
        "transaction": transaction,
        "message": "مبلغ با موفقیت از کیف پول کسر شد",
    }


# =========================================================
# Subscription & Promotion Purchases
# =========================================================

@router.post("/buy-subscription", response_model=SubscriptionOperationResponse)
def buy_subscription(
    payload: BuySubscriptionRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """خرید پلن اشتراک با کسر از موجودی کیف پول"""
    wallet, transaction, subscription = DoctorWalletService.buy_subscription(
        db=db,
        doctor_id=current_doctor.id,
        plan_id=payload.plan_id,
        reference_id=payload.reference_id,
    )
    return {
        "wallet": wallet,
        "transaction": transaction,
        "subscription_id": subscription.id,
        "starts_at": subscription.starts_at,
        "ends_at": subscription.ends_at,
        "message": "اشتراک با موفقیت فعال شد",
    }


@router.post("/buy-promotion", response_model=PromotionOperationResponse)
def buy_promotion(
    payload: BuyPromotionRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """خرید بسته ارتقا و پروموشن با کسر از موجودی کیف پول"""
    wallet, transaction, promo = DoctorWalletService.buy_promotion(
        db=db,
        doctor_id=current_doctor.id,
        package_id=payload.package_id,
        reference_id=payload.reference_id,
    )
    return {
        "wallet": wallet,
        "transaction": transaction,
        "promotion_id": promo.id,
        "starts_at": promo.starts_at,
        "ends_at": promo.ends_at,
        "message": "بسته پروموشن با موفقیت فعال شد",
    }


# =========================================================
# Mellat Payment Gateway Endpoints
# =========================================================

@router.post("/init-payment", response_model=PaymentInitResponse)
def init_payment(
    payload: PaymentInitRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """شروع فرآیند پرداخت آنلاین از طریق درگاه ملت"""
    payment = DoctorPayment(
        doctor_id=current_doctor.id,
        amount=payload.amount,
        gateway="mellat",
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    gateway = MellatPaymentGateway()
    callback_base = getattr(settings, "PAYMENT_CALLBACK_BASE_URL", "http://127.0.0.1:8000")
    callback_url = f"{callback_base}/api/v1/doctor-wallet/callback/mellat"

    init_res = gateway.create_payment(
        amount=int(payload.amount),
        order_id=str(payment.id),
        callback_url=callback_url,
    )

    payment.authority = init_res.authority
    db.commit()

    return {
        "payment_id": payment.id,
        "authority": init_res.authority,
        "payment_url": init_res.payment_url,
    }


@router.post("/callback/mellat", response_class=HTMLResponse)
def callback_mellat(
    db: Session = Depends(get_db),
    ResCode: str = Form(...),
    SaleOrderId: str = Form(...),
    SaleReferenceId: str = Form(None),
    RefId: str = Form(None),
):
    """هندلر بازگشت از درگاه بانک ملت (Verify و Settle تراکنش)"""
    payment = db.query(DoctorPayment).filter(DoctorPayment.id == int(SaleOrderId)).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="شناسه تراکنش پرداخت یافت نشد")

    if payment.status == "paid":
        return "<h3>تراکنش قبلاً با موفقیت تایید و کیف پول شارژ شده است.</h3>"

    if ResCode != "0" or not SaleReferenceId:
        payment.status = "failed"
        payment.description = f"تراکنش توسط کاربر لغو شد یا با خطا مواجه شد. ResCode: {ResCode}"
        db.commit()
        return f"<h3>پرداخت ناموفق بود. کد خطا: {ResCode}</h3>"

    gateway = MellatPaymentGateway()

    # 1. تایید تراکنش (Verify)
    if not gateway.verify_payment(order_id=str(payment.id), sale_order_id=SaleOrderId, sale_reference_id=SaleReferenceId):
        payment.status = "failed"
        payment.description = "خطا در تایید تراکنش (bpVerifyRequest)"
        db.commit()
        return "<h3>تایید پرداخت از سمت بانک انجام نشد.</h3>"

    # 2. تسویه تراکنش (Settle)
    if not gateway.settle_payment(order_id=str(payment.id), sale_order_id=SaleOrderId, sale_reference_id=SaleReferenceId):
        payment.status = "failed"
        payment.description = "خطا در تسویه نهایی تراکنش (bpSettleRequest)"
        db.commit()
        return "<h3>تسویه نهایی تراکنش در درگاه بانک ناموفق بود.</h3>"

    # 3. ثبت قطعی و شارژ کیف پول پزشک
    payment.status = "paid"
    payment.sale_reference_id = SaleReferenceId
    payment.description = "پرداخت موفق و تسویه‌شده از درگاه ملت"

    DoctorWalletService.top_up(
        db=db,
        doctor_id=payment.doctor_id,
        amount=payment.amount,
        reference_id=str(SaleReferenceId),
        description=f"شارژ آنلاین کیف پول از طریق درگاه ملت (شناسه پرداخت: {payment.id})",
    )

    db.commit()
    return "<h3>پرداخت با موفقیت انجام شد و کیف پول شما شارژ گردید. می‌توانید این صفحه را ببندید.</h3>"
