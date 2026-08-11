from datetime import datetime, timezone, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.doctor_wallet import DoctorWallet, DoctorWalletTransaction
from app.models.doctor_billing import (
    DoctorPromotion,
    DoctorSubscription,
    PromotionPackage,
    SubscriptionPlan,
)


class DoctorWalletService:
    @staticmethod
    def get_or_create_wallet(db: Session, doctor_id: int) -> DoctorWallet:
        wallet = db.query(DoctorWallet).filter(DoctorWallet.doctor_id == doctor_id).first()

        if wallet:
            if not wallet.is_active:
                wallet.is_active = True
                try:
                    db.commit()
                    db.refresh(wallet)
                except Exception as e:
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to activate doctor wallet: {str(e)}",
                    )
            return wallet

        wallet = DoctorWallet(
            doctor_id=doctor_id,
            balance=Decimal("0.00"),
            is_active=True,
        )

        db.add(wallet)

        try:
            db.commit()
            db.refresh(wallet)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create doctor wallet: {str(e)}",
            )

        return wallet

    @staticmethod
    def list_transactions(db: Session, doctor_id: int):
        wallet = DoctorWalletService.get_or_create_wallet(db, doctor_id)

        return (
            db.query(DoctorWalletTransaction)
            .filter(DoctorWalletTransaction.wallet_id == wallet.id)
            .order_by(DoctorWalletTransaction.created_at.desc())
            .all()
        )

    @staticmethod
    def top_up(
        db: Session,
        doctor_id: int,
        amount: Decimal,
        reference_id: str | None = None,
        description: str | None = None,
    ):
        amount = Decimal(str(amount))

        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be greater than zero",
            )

        wallet = DoctorWalletService.get_or_create_wallet(db, doctor_id)

        tx = DoctorWalletTransaction(
            wallet_id=wallet.id,
            transaction_type="topup",
            amount=amount,
            reference_id=reference_id,
            description=description or "Wallet top-up",
        )

        try:
            db.add(tx)

            db.execute(
                update(DoctorWallet)
                .where(DoctorWallet.id == wallet.id)
                .values(balance=DoctorWallet.balance + amount)
            )

            db.commit()
            db.refresh(wallet)
            db.refresh(tx)

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transaction failed: {str(e)}",
            )

        return wallet, tx

    @staticmethod
    def debit(
        db: Session,
        doctor_id: int,
        amount: Decimal,
        transaction_type: str,
        description: str | None = None,
        reference_id: str | None = None,
        commit_transaction: bool = True,
    ):
        amount = Decimal(str(amount))

        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be greater than zero",
            )

        wallet = DoctorWalletService.get_or_create_wallet(db, doctor_id)

        tx = DoctorWalletTransaction(
            wallet_id=wallet.id,
            transaction_type=transaction_type,
            amount=amount,
            reference_id=reference_id,
            description=description,
        )

        try:
            db.add(tx)

            result = db.execute(
                update(DoctorWallet)
                .where(
                    DoctorWallet.id == wallet.id,
                    DoctorWallet.balance >= amount,
                )
                .values(balance=DoctorWallet.balance - amount)
            )

            if result.rowcount != 1:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient wallet balance",
                )

            if commit_transaction:
                db.commit()
                db.refresh(wallet)
                db.refresh(tx)

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Debit transaction failed: {str(e)}",
            )

        return wallet, tx

    @staticmethod
    def buy_subscription(
        db: Session,
        doctor_id: int,
        plan_id: int,
        reference_id: str | None = None,
    ):
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

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        wallet, tx = DoctorWalletService.debit(
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

        starts_at = current_subscription.ends_at if current_subscription else now

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

        db.add(subscription)

        try:
            db.commit()
            db.refresh(wallet)
            db.refresh(tx)
            db.refresh(subscription)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Subscription purchase failed during save: {str(e)}",
            )

        return wallet, tx, subscription

    @staticmethod
    def buy_promotion(
        db: Session,
        doctor_id: int,
        package_id: int,
        reference_id: str | None = None,
    ):
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

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        wallet, tx = DoctorWalletService.debit(
            db=db,
            doctor_id=doctor_id,
            amount=Decimal(str(package.price)),
            transaction_type="promotion",
            description=f"Promotion purchase: {package.name}",
            reference_id=reference_id,
            commit_transaction=False,
        )

        starts_at = now
        ends_at = now + timedelta(days=package.duration_days)

        promotion = DoctorPromotion(
            doctor_id=doctor_id,
            package_id=package.id,
            starts_at=starts_at,
            ends_at=ends_at,
            is_active=True,
        )

        db.add(promotion)

        try:
            db.commit()
            db.refresh(wallet)
            db.refresh(tx)
            db.refresh(promotion)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Promotion purchase failed during save: {str(e)}",
            )

        return wallet, tx, promotion
