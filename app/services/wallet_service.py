# Path: app/services/wallet_service.py

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.models.user import User
from app.models.wallet import (
    Wallet,
    Transaction,
    TransactionType,
    TransactionStatus,
)

logger = get_logger(__name__)


class WalletService:
    MONEY_PRECISION = Decimal("0.01")

    # =========================================================
    # Internal Helpers
    # =========================================================

    @staticmethod
    def _to_decimal(value) -> Decimal:
        """
        تبدیل امن مقدار پول به Decimal با دقت دو رقم اعشار.
        """
        try:
            decimal_value = Decimal(str(value))
        except Exception as exc:
            logger.exception(
                "Invalid money format in _to_decimal: value=%r",
                value,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فرمت مبلغ نامعتبر است",
            ) from exc

        return decimal_value.quantize(
            WalletService.MONEY_PRECISION,
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def _validate_positive_amount(amount: Decimal) -> None:
        """
        مبلغ باید حتماً بزرگ‌تر از صفر باشد.
        """
        if amount <= Decimal("0.00"):
            logger.warning(
                "Invalid non-positive amount: amount=%s",
                amount,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="مبلغ باید بیشتر از صفر باشد",
            )

    @staticmethod
    def _lock_wallets(
        db: Session,
        wallet_ids: List[int],
    ) -> List[Wallet]:
        """
        قفل‌کردن کیف پول‌ها برای جلوگیری از race condition.

        کیف پول‌ها بر اساس id مرتب قفل می‌شوند تا احتمال deadlock
        در عملیات انتقال کاهش پیدا کند.
        """
        sorted_ids = sorted(set(wallet_ids))

        if not sorted_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="شناسه کیف پول معتبر نیست",
            )

        try:
            wallets = (
                db.query(Wallet)
                .filter(Wallet.id.in_(sorted_ids))
                .order_by(Wallet.id.asc())
                .with_for_update()
                .all()
            )
        except Exception as exc:
            logger.exception(
                "Failed to lock wallets: wallet_ids=%s",
                sorted_ids,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در قفل کردن کیف پول‌ها",
            ) from exc

        if len(wallets) != len(sorted_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="کیف پول یافت نشد",
            )

        return wallets

    @staticmethod
    def _get_locked_transaction(
        db: Session,
        transaction_id: int,
    ) -> Transaction:
        """
        دریافت تراکنش و قفل‌کردن آن برای جلوگیری از refund تکراری.
        """
        transaction = (
            db.query(Transaction)
            .filter(Transaction.id == transaction_id)
            .with_for_update()
            .first()
        )

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="تراکنش یافت نشد",
            )

        return transaction

    # =========================================================
    # Wallet Core
    # =========================================================

    @staticmethod
    def get_or_create_wallet(
        db: Session,
        user_id: int,
        commit: bool = True,
    ) -> Wallet:
        """
        دریافت کیف پول کاربر یا ساخت کیف پول جدید.
        """
        wallet = (
            db.query(Wallet)
            .filter(Wallet.user_id == user_id)
            .first()
        )

        if wallet:
            return wallet

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="کاربر یافت نشد",
            )

        wallet = Wallet(
            user_id=user_id,
            balance=Decimal("0.00"),
            is_active=True,
            is_locked=False,
        )

        db.add(wallet)

        try:
            if commit:
                db.commit()
                db.refresh(wallet)
            else:
                db.flush()
        except Exception as exc:
            db.rollback()
            logger.exception(
                "Failed to create wallet for user_id=%s",
                user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در ایجاد کیف پول",
            ) from exc

        return wallet

    # =========================================================
    # Immediate Deposit
    # =========================================================

    @staticmethod
    def deposit(
        db: Session,
        user_id: int,
        amount: Decimal,
        description: str = "شارژ کیف پول",
        commit: bool = True,
    ) -> Transaction:
        """
        شارژ مستقیم کیف پول.

        این متد برای شارژهایی استفاده می‌شود که قبلاً خارج از درگاه
        پرداخت تأیید شده‌اند؛ مانند تست‌ها، ادمین یا عملیات داخلی.

        تفاوت این متد با create_pending_deposit:
        - deposit موجودی را بلافاصله افزایش می‌دهد.
        - create_pending_deposit فقط تراکنش pending ایجاد می‌کند.
        """
        amount_dec = WalletService._to_decimal(amount)
        WalletService._validate_positive_amount(amount_dec)

        wallet = WalletService.get_or_create_wallet(
            db=db,
            user_id=user_id,
            commit=False,
        )

        locked_wallets = WalletService._lock_wallets(
            db=db,
            wallet_ids=[wallet.id],
        )
        wallet = locked_wallets[0]

        transaction = Transaction(
            receiver_wallet_id=wallet.id,
            amount=amount_dec,
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.SUCCESS,
            tracking_code=f"DEP-{uuid.uuid4().hex[:12].upper()}",
            description=description,
        )

        wallet.balance = (
            WalletService._to_decimal(wallet.balance) + amount_dec
        )

        db.add(transaction)

        try:
            if commit:
                db.commit()
                db.refresh(wallet)
                db.refresh(transaction)
            else:
                db.flush()
        except Exception as exc:
            db.rollback()
            logger.exception(
                "Failed to deposit into wallet: user_id=%s amount=%s",
                user_id,
                amount_dec,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در شارژ کیف پول",
            ) from exc

        logger.info(
            "Wallet deposit completed: user_id=%s amount=%s transaction_id=%s",
            user_id,
            amount_dec,
            transaction.id,
        )

        return transaction

    # =========================================================
    # Pending Deposit Flow
    # =========================================================

    @staticmethod
    def create_pending_deposit(
        db: Session,
        user_id: int,
        amount: Decimal,
        description: str = "شارژ کیف پول (در انتظار پرداخت)",
    ) -> Transaction:
        """
        ایجاد تراکنش pending بدون افزایش موجودی.
        """
        amount_dec = WalletService._to_decimal(amount)
        WalletService._validate_positive_amount(amount_dec)

        wallet = WalletService.get_or_create_wallet(
            db=db,
            user_id=user_id,
            commit=False,
        )

        authority = f"DEP-{uuid.uuid4().hex[:12].upper()}"

        transaction = Transaction(
            receiver_wallet_id=wallet.id,
            amount=amount_dec,
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.PENDING,
            tracking_code=authority,
            description=description,
        )

        db.add(transaction)

        try:
            db.commit()
            db.refresh(transaction)
        except Exception as exc:
            db.rollback()
            logger.exception(
                "Failed to create pending deposit for user_id=%s",
                user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در ایجاد تراکنش شارژ",
            ) from exc

        logger.info(
            "Pending deposit created: user_id=%s authority=%s",
            user_id,
            authority,
        )

        return transaction

    @staticmethod
    def verify_deposit(
        db: Session,
        authority: str,
        is_bank_successful: bool,
    ) -> Transaction:
        """
        تأیید نهایی تراکنش pending به‌شکل idempotent.
        """
        transaction = (
            db.query(Transaction)
            .filter(Transaction.tracking_code == authority)
            .with_for_update()
            .first()
        )

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="تراکنش یافت نشد",
            )

        if transaction.status in (
            TransactionStatus.SUCCESS,
            TransactionStatus.FAILED,
        ):
            return transaction

        if transaction.status != TransactionStatus.PENDING:
            return transaction

        if is_bank_successful:
            wallet = (
                db.query(Wallet)
                .filter(Wallet.id == transaction.receiver_wallet_id)
                .with_for_update()
                .first()
            )

            if not wallet:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="کیف پول مقصد یافت نشد",
                )

            wallet.balance = (
                WalletService._to_decimal(wallet.balance)
                + transaction.amount
            )
            transaction.status = TransactionStatus.SUCCESS

        else:
            transaction.status = TransactionStatus.FAILED

        try:
            db.commit()
            db.refresh(transaction)
        except Exception as exc:
            db.rollback()
            logger.exception(
                "Failed to verify deposit: authority=%s",
                authority,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در ثبت نهایی تراکنش",
            ) from exc

        return transaction

    # =========================================================
    # Transfer
    # =========================================================

    @staticmethod
    def transfer_fee(
        db: Session,
        patient_id: int,
        doctor_id: int,
        amount: Decimal,
        appointment_id: Optional[int] = None,
        commit: bool = True,
    ) -> Transaction:
        """
        انتقال هزینه ویزیت از بیمار به پزشک.
        """
        amount_dec = WalletService._to_decimal(amount)
        WalletService._validate_positive_amount(amount_dec)

        patient_wallet = WalletService.get_or_create_wallet(
            db=db,
            user_id=patient_id,
            commit=False,
        )

        doctor_wallet = WalletService.get_or_create_wallet(
            db=db,
            user_id=doctor_id,
            commit=False,
        )

        wallets = WalletService._lock_wallets(
            db=db,
            wallet_ids=[
                patient_wallet.id,
                doctor_wallet.id,
            ],
        )

        patient_wallet = next(
            wallet for wallet in wallets
            if wallet.id == patient_wallet.id
        )
        doctor_wallet = next(
            wallet for wallet in wallets
            if wallet.id == doctor_wallet.id
        )

        if patient_wallet.balance < amount_dec:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="موجودی کیف پول بیمار کافی نیست",
            )

        transaction = Transaction(
            sender_wallet_id=patient_wallet.id,
            receiver_wallet_id=doctor_wallet.id,
            amount=amount_dec,
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.SUCCESS,
            appointment_id=appointment_id,
            tracking_code=f"TRX-{uuid.uuid4().hex[:10].upper()}",
            description=(
                f"پرداخت ویزیت نوبت {appointment_id}"
                if appointment_id
                else "پرداخت حق ویزیت"
            ),
        )

        patient_wallet.balance -= amount_dec
        doctor_wallet.balance += amount_dec

        db.add(transaction)

        try:
            if commit:
                db.commit()
                db.refresh(transaction)
            else:
                db.flush()
        except Exception as exc:
            db.rollback()
            logger.exception(
                "Failed to transfer fee: patient_id=%s doctor_id=%s amount=%s",
                patient_id,
                doctor_id,
                amount_dec,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در انتقال وجه",
            ) from exc

        return transaction

    # =========================================================
    # Refund
    # =========================================================

    @staticmethod
    def refund(
        db: Session,
        transaction_id: int,
        description: str = "بازگشت وجه",
        commit: bool = True,
    ) -> Transaction:
        """
        برگشت وجه یک تراکنش انتقال از پزشک به بیمار.

        برای تراکنش اصلی:
        sender_wallet   = کیف پول بیمار
        receiver_wallet = کیف پول پزشک

        در refund:
        sender_wallet   = کیف پول پزشک
        receiver_wallet = کیف پول بیمار
        """
        original_transaction = WalletService._get_locked_transaction(
            db=db,
            transaction_id=transaction_id,
        )

        if original_transaction.transaction_type != TransactionType.TRANSFER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فقط تراکنش انتقال قابل برگشت است",
            )

        if original_transaction.status != TransactionStatus.SUCCESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فقط تراکنش موفق قابل برگشت است",
            )

        if not original_transaction.sender_wallet_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="کیف پول بیمار در تراکنش یافت نشد",
            )

        if not original_transaction.receiver_wallet_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="کیف پول پزشک در تراکنش یافت نشد",
            )

        existing_refund = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_type == TransactionType.REFUND,
                Transaction.appointment_id == original_transaction.appointment_id,
            )
            .first()
        )

        if (
            original_transaction.appointment_id is not None
            and existing_refund is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این تراکنش قبلاً برگشت داده شده است",
            )

        wallets = WalletService._lock_wallets(
            db=db,
            wallet_ids=[
                original_transaction.sender_wallet_id,
                original_transaction.receiver_wallet_id,
            ],
        )

        patient_wallet = next(
            wallet
            for wallet in wallets
            if wallet.id == original_transaction.sender_wallet_id
        )

        doctor_wallet = next(
            wallet
            for wallet in wallets
            if wallet.id == original_transaction.receiver_wallet_id
        )

        amount_dec = WalletService._to_decimal(
            original_transaction.amount
        )

        if doctor_wallet.balance < amount_dec:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="موجودی کیف پول پزشک برای بازگشت وجه کافی نیست",
            )

        refund_transaction = Transaction(
            sender_wallet_id=doctor_wallet.id,
            receiver_wallet_id=patient_wallet.id,
            amount=amount_dec,
            transaction_type=TransactionType.REFUND,
            status=TransactionStatus.SUCCESS,
            appointment_id=original_transaction.appointment_id,
            tracking_code=f"REF-{uuid.uuid4().hex[:10].upper()}",
            description=description,
        )

        doctor_wallet.balance -= amount_dec
        patient_wallet.balance += amount_dec

        db.add(refund_transaction)

        try:
            if commit:
                db.commit()
                db.refresh(refund_transaction)
            else:
                db.flush()
        except Exception as exc:
            db.rollback()
            logger.exception(
                "Failed to refund transaction_id=%s",
                transaction_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در بازگشت وجه",
            ) from exc

        logger.info(
            "Refund completed: original_transaction_id=%s refund_transaction_id=%s",
            transaction_id,
            refund_transaction.id,
        )

        return refund_transaction

    # =========================================================
    # History
    # =========================================================

    @staticmethod
    def get_wallet_history(
        db: Session,
        user_id: int,
    ) -> List[Transaction]:
        wallet = (
            db.query(Wallet)
            .filter(Wallet.user_id == user_id)
            .first()
        )

        if not wallet:
            return []

        return (
            db.query(Transaction)
            .filter(
                (Transaction.sender_wallet_id == wallet.id)
                | (Transaction.receiver_wallet_id == wallet.id)
            )
            .order_by(Transaction.created_at.desc())
            .all()
        )
