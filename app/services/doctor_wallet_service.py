# Path: app/services/doctor_wallet_service.py

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.doctor_billing import (
    DoctorPromotion,
    DoctorSubscription,
    PromotionPackage,
    SubscriptionPlan,
)
from app.models.doctor_wallet import (
    DoctorWallet,
    DoctorWalletTransaction,
)


class DoctorWalletService:
    MONEY_PRECISION = Decimal("0.01")

    # =========================================================
    # Internal helpers
    # =========================================================

    @staticmethod
    def _normalize_amount(amount: Decimal) -> Decimal:
        """تبدیل امن مبلغ به Decimal با دو رقم اعشار."""
        try:
            normalized_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid amount format",
            ) from exc

        if not normalized_amount.is_finite():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be a finite number",
            )

        normalized_amount = normalized_amount.quantize(
            DoctorWalletService.MONEY_PRECISION,
            rounding=ROUND_HALF_UP,
        )

        if normalized_amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be greater than zero",
            )

        return normalized_amount

    @staticmethod
    def _normalize_reference_id(
        reference_id: Optional[str],
    ) -> Optional[str]:
        """حذف فاصله‌های اضافی reference_id."""
        if reference_id is None:
            return None

        normalized_reference = str(reference_id).strip()

        if not normalized_reference:
            return None

        if len(normalized_reference) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reference_id is too long",
            )

        return normalized_reference

    @staticmethod
    def _ensure_unique_reference_id(
        db: Session,
        wallet_id: int,
        reference_id: Optional[str],
    ) -> None:
        """جلوگیری از اجرای تکراری عملیات مالی با reference_id یکسان."""
        if reference_id is None:
            return

        existing_transaction = (
            db.query(DoctorWalletTransaction)
            .filter(
                DoctorWalletTransaction.wallet_id == wallet_id,
                DoctorWalletTransaction.reference_id == reference_id,
            )
            .first()
        )

        if existing_transaction:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This financial operation has already been processed with this reference_id.",
            )

    @staticmethod
    def _handle_integrity_error(
        db: Session,
        exc: IntegrityError,
    ) -> None:
        """تبدیل خطای دیتابیس مربوط به unique reference_id به پاسخ HTTP مناسب."""
        db.rollback()
        error_text = str(exc.orig).lower()

        if (
            "uq_doctor_wallet_transaction_wallet_reference" in error_text
            or "doctor_wallet_transactions.wallet_id" in error_text
            or "unique constraint failed" in error_text
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This financial operation has already been processed with this reference_id.",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Financial transaction could not be completed",
        ) from exc

    # =========================================================
    # Wallet core
    # =========================================================

    @staticmethod
    def get_or_create_wallet(
        db: Session,
        doctor_id: int,
        commit: bool = True,
    ) -> DoctorWallet:
        """دریافت یا ایجاد کیف پول پزشک."""
        wallet = (
            db.query(DoctorWallet)
            .filter(DoctorWallet.doctor_id == doctor_id)
            .first()
        )

        if wallet:
            if not wallet.is_active:
                wallet.is_active = True
                try:
                    if commit:
                        db.commit()
                        db.refresh(wallet)
                    else:
                        db.flush()
                except Exception as exc:
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to activate doctor wallet",
                    ) from exc

            return wallet

        wallet = DoctorWallet(
            doctor_id=doctor_id,
            balance=Decimal("0.00"),
            is_active=True,
        )

        db.add(wallet)

        try:
            if commit:
                db.commit()
                db.refresh(wallet)
            else:
                db.flush()
        except IntegrityError as exc:
            db.rollback()
            existing_wallet = (
                db.query(DoctorWallet)
                .filter(DoctorWallet.doctor_id == doctor_id)
                .first()
            )
            if existing_wallet:
                return existing_wallet

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create doctor wallet",
            ) from exc
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create doctor wallet",
            ) from exc

        return wallet

    @staticmethod
    def get_transactions(
        db: Session,
        doctor_id: int,
    ) -> List[DoctorWalletTransaction]:
        """لیست تراکنش‌های کیف پول پزشک."""
        wallet = DoctorWalletService.get_or_create_wallet(
            db=db,
            doctor_id=doctor_id,
        )

        return (
            db.query(DoctorWalletTransaction)
            .filter(DoctorWalletTransaction.wallet_id == wallet.id)
            .order_by(DoctorWalletTransaction.created_at.desc())
            .all()
        )

    # برای سازگاری با هر دو نام
    list_transactions = get_transactions

    # =========================================================
    # Top-up
    # =========================================================

    @staticmethod
    def top_up(
        db: Session,
        doctor_id: int,
        amount: Decimal,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[DoctorWallet, DoctorWalletTransaction]:
        """افزایش امن موجودی کیف پول پزشک."""
        normalized_amount = DoctorWalletService._normalize_amount(amount)
        normalized_reference_id = DoctorWalletService._normalize_reference_id(reference_id)

        wallet = DoctorWalletService.get_or_create_wallet(
            db=db,
            doctor_id=doctor_id,
            commit=False,
        )

        DoctorWalletService._ensure_unique_reference_id(
            db=db,
            wallet_id=wallet.id,
            reference_id=normalized_reference_id,
        )

        transaction = DoctorWalletTransaction(
            wallet_id=wallet.id,
            transaction_type="topup",
            amount=normalized_amount,
            reference_id=normalized_reference_id,
            description=description or "Wallet top-up",
        )

        try:
            db.add(transaction)

            db.execute(
                update(DoctorWallet)
                .where(
                    DoctorWallet.id == wallet.id,
                    DoctorWallet.is_active.is_(True),
                )
                .values(
                    balance=DoctorWallet.balance + normalized_amount,
                )
            )

            db.commit()
            db.refresh(wallet)
            db.refresh(transaction)

        except IntegrityError as exc:
            DoctorWalletService._handle_integrity_error(db, exc)

        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Wallet top-up transaction failed",
            ) from exc

        return wallet, transaction

    # =========================================================
    # Debit
    # =========================================================

    @staticmethod
    def debit(
        db: Session,
        doctor_id: int,
        amount: Decimal,
        transaction_type: str = "debit",
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        commit_transaction: bool = True,
    ) -> Tuple[DoctorWallet, DoctorWalletTransaction]:
        """کسر اتمیک و امن موجودی کیف پول با تضمین عدم منفی شدن."""
        normalized_amount = DoctorWalletService._normalize_amount(amount)
        normalized_reference_id = DoctorWalletService._normalize_reference_id(reference_id)

        if not transaction_type or not str(transaction_type).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="transaction_type is required",
            )

        wallet = DoctorWalletService.get_or_create_wallet(
            db=db,
            doctor_id=doctor_id,
            commit=False,
        )

        DoctorWalletService._ensure_unique_reference_id(
            db=db,
            wallet_id=wallet.id,
            reference_id=normalized_reference_id,
        )

        transaction = DoctorWalletTransaction(
            wallet_id=wallet.id,
            transaction_type=str(transaction_type).strip().lower(),
            amount=-normalized_amount,
            reference_id=normalized_reference_id,
            description=description,
        )

        try:
            db.add(transaction)

            update_result = db.execute(
                update(DoctorWallet)
                .where(
                    DoctorWallet.id == wallet.id,
                    DoctorWallet.is_active.is_(True),
                    DoctorWallet.balance >= normalized_amount,
                )
                .values(
                    balance=DoctorWallet.balance - normalized_amount,
                )
            )

            if update_result.rowcount != 1:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient wallet balance",
                )

            if commit_transaction:
                db.commit()
                db.refresh(wallet)
                db.refresh(transaction)
            else:
                db.flush()

        except HTTPException:
            raise

        except IntegrityError as exc:
            DoctorWalletService._handle_integrity_error(db, exc)

        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Wallet debit transaction failed",
            ) from exc

        return wallet, transaction

    # =========================================================
    # Subscription
    # =========================================================

    @staticmethod
    def buy_subscription(
        db: Session,
        doctor_id: int,
        plan_id: int,
        reference_id: Optional[str] = None,
    ) -> Tuple[DoctorWallet, DoctorWalletTransaction, DoctorSubscription]:
        """خرید یا تمدید اشتراک در یک ترنزکشن اتمیک."""
        plan = (
            db.query(SubscriptionPlan)
            .filter(
                SubscriptionPlan.id == plan_id,
                SubscriptionPlan.is_active.is_(True),
            )
            .first()
        )

        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription plan not found",
            )

        now = datetime.utcnow()

        wallet, transaction = DoctorWalletService.debit(
            db=db,
            doctor_id=doctor_id,
            amount=Decimal(str(plan.price)),
            transaction_type="subscription",
            description=f"Subscription purchase: {plan.name}",
            reference_id=reference_id,
            commit_transaction=False,
        )

        current_subscription = (
            db.query(DoctorSubscription)
            .filter(
                DoctorSubscription.doctor_id == doctor_id,
                DoctorSubscription.is_active.is_(True),
                DoctorSubscription.ends_at > now,
            )
            .order_by(DoctorSubscription.ends_at.desc())
            .first()
        )

        starts_at = (
            current_subscription.ends_at
            if current_subscription
            else now
        )

        if starts_at < now:
            starts_at = now

        ends_at = starts_at + timedelta(days=plan.duration_days)

        subscription = DoctorSubscription(
            doctor_id=doctor_id,
            plan_id=plan.id,
            starts_at=starts_at,
            ends_at=ends_at,
            is_active=True,
        )

        try:
            db.add(subscription)
            db.commit()

            db.refresh(wallet)
            db.refresh(transaction)
            db.refresh(subscription)

        except IntegrityError as exc:
            DoctorWalletService._handle_integrity_error(db, exc)

        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Subscription purchase failed",
            ) from exc

        return wallet, transaction, subscription

    # =========================================================
    # Promotion
    # =========================================================

    @staticmethod
    def buy_promotion(
        db: Session,
        doctor_id: int,
        package_id: int,
        reference_id: Optional[str] = None,
    ) -> Tuple[DoctorWallet, DoctorWalletTransaction, DoctorPromotion]:
        """خرید پکیج ارتقا/پروموشن در یک ترنزکشن اتمیک."""
        package = (
            db.query(PromotionPackage)
            .filter(
                PromotionPackage.id == package_id,
                PromotionPackage.is_active.is_(True),
            )
            .first()
        )

        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promotion package not found",
            )

        now = datetime.utcnow()

        wallet, transaction = DoctorWalletService.debit(
            db=db,
            doctor_id=doctor_id,
            amount=Decimal(str(package.price)),
            transaction_type="promotion",
            description=f"Promotion purchase: {package.name}",
            reference_id=reference_id,
            commit_transaction=False,
        )

        promotion = DoctorPromotion(
            doctor_id=doctor_id,
            package_id=package.id,
            starts_at=now,
            ends_at=now + timedelta(days=package.duration_days),
            is_active=True,
        )

        try:
            db.add(promotion)
            db.commit()

            db.refresh(wallet)
            db.refresh(transaction)
            db.refresh(promotion)

        except IntegrityError as exc:
            DoctorWalletService._handle_integrity_error(db, exc)

        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Promotion purchase failed",
            ) from exc

        return wallet, transaction, promotion
