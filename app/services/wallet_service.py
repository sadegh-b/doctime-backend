# app/services/wallet_service.py

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

    # ==========================
    # Internal Helpers
    # ==========================

    @staticmethod
    def _to_decimal(value) -> Decimal:
        """
        تبدیل ایمن مقدار به Decimal جهت جلوگیری از خطاهای float precision.
        """
        try:
            decimal_value = Decimal(str(value))
        except Exception as exc:
            logger.exception("Invalid money format in _to_decimal: value=%r", value)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فرمت مبلغ نامعتبر است"
            ) from exc

        decimal_value = decimal_value.quantize(
            WalletService.MONEY_PRECISION,
            rounding=ROUND_HALF_UP
        )

        return decimal_value

    @staticmethod
    def _validate_positive_amount(amount: Decimal):
        if amount <= Decimal("0.00"):
            logger.warning("Invalid non-positive amount received: amount=%s", amount)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="مبلغ باید بیشتر از صفر باشد"
            )

    @staticmethod
    def _lock_wallets(
            db: Session,
            wallet_ids: List[int]
    ) -> List[Wallet]:
        """
        قفل کردن deterministic برای جلوگیری از deadlock در تراکنش‌های همزمان.
        """
        sorted_ids = sorted(set(wallet_ids))

        try:
            wallets = (
                db.query(Wallet)
                .filter(Wallet.id.in_(sorted_ids))
                .order_by(Wallet.id.asc())
                .with_for_update()
                .all()
            )
        except Exception as exc:
            logger.exception("Failed to lock wallets: wallet_ids=%s", sorted_ids)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در قفل کردن کیف پول‌ها"
            ) from exc

        if len(wallets) != len(sorted_ids):
            logger.warning(
                "Wallet not found while locking. requested=%s found=%s",
                sorted_ids,
                [wallet.id for wallet in wallets],
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="کیف پول یافت نشد"
            )

        return wallets

    # ==========================
    # Wallet Core
    # ==========================

    @staticmethod
    def get_or_create_wallet(
            db: Session,
            user_id: int,
            commit: bool = True
    ) -> Wallet:
        """
        دریافت یا ساخت کیف پول کاربر با کنترل کامیت تراکنش.
        """
        try:
            wallet = (
                db.query(Wallet)
                .filter(Wallet.user_id == user_id)
                .first()
            )
        except Exception as exc:
            logger.exception("Database error in get_or_create_wallet (fetch wallet): user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در دریافت کیف پول"
            ) from exc

        if wallet:
            return wallet

        try:
            user = (
                db.query(User)
                .filter(User.id == user_id)
                .first()
            )
        except Exception as exc:
            logger.exception("Database error in get_or_create_wallet (fetch user): user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در بررسی کاربر"
            ) from exc

        if not user:
            logger.warning("User not found for wallet creation: user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="کاربر یافت نشد"
            )

        wallet = Wallet(
            user_id=user_id,
            balance=Decimal("0.00")
        )

        db.add(wallet)

        if commit:
            try:
                db.commit()
                db.refresh(wallet)
                logger.info("Wallet created successfully: user_id=%s wallet_id=%s", user_id, wallet.id)
                return wallet
            except Exception as exc:
                db.rollback()
                logger.exception("Failed to create wallet with commit: user_id=%s", user_id)

                # تلاش مجدد برای هندل Race Condition
                existing_wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
                if existing_wallet:
                    return existing_wallet
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="خطا در ساخت کیف پول"
                ) from exc
        else:
            try:
                db.flush()
                logger.info("Wallet created in-memory (Flushed): user_id=%s", user_id)
                return wallet
            except Exception as exc:
                logger.exception("Failed to create wallet with flush: user_id=%s", user_id)

                # تلاش مجدد بدون تراکنش جدید
                existing_wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
                if existing_wallet:
                    return existing_wallet
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="خطا در ساخت کیف پول"
                ) from exc

    # ==========================
    # Deposit
    # ==========================

    @staticmethod
    def deposit(
            db: Session,
            user_id: int,
            amount: Decimal,
            description: str = "شارژ کیف پول",
            commit: bool = True
    ) -> Transaction:
        amount_dec = WalletService._to_decimal(amount)
        WalletService._validate_positive_amount(amount_dec)

        logger.info(
            "Deposit requested: user_id=%s amount=%s description=%s commit=%s",
            user_id,
            amount_dec,
            description,
            commit
        )

        wallet = WalletService.get_or_create_wallet(db=db, user_id=user_id, commit=commit)

        try:
            locked_wallet = (
                db.query(Wallet)
                .filter(Wallet.id == wallet.id)
                .with_for_update()
                .first()
            )
        except Exception as exc:
            logger.exception("Failed to lock wallet for deposit: wallet_id=%s", wallet.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در قفل کردن کیف پول"
            ) from exc

        if not locked_wallet:
            logger.warning("Wallet not found during deposit lock: wallet_id=%s", wallet.id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="کیف پول یافت نشد"
            )

        tracking_code = f"DEP-{uuid.uuid4().hex[:10].upper()}"

        transaction = Transaction(
            receiver_wallet_id=locked_wallet.id,
            amount=amount_dec,
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.SUCCESS,
            tracking_code=tracking_code,
            description=description,
        )

        locked_wallet.balance = (
                WalletService._to_decimal(locked_wallet.balance) + amount_dec
        )

        db.add(transaction)

        if commit:
            try:
                db.commit()
                db.refresh(transaction)
                logger.info(
                    "Deposit successful (Committed): user_id=%s wallet_id=%s amount=%s tracking_code=%s",
                    user_id,
                    locked_wallet.id,
                    amount_dec,
                    tracking_code
                )
            except Exception as exc:
                db.rollback()
                logger.exception(
                    "Deposit commit failed: user_id=%s wallet_id=%s amount=%s",
                    user_id,
                    locked_wallet.id,
                    amount_dec
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="خطا در شارژ کیف پول"
                ) from exc
        else:
            db.flush()
            logger.info("Deposit processed (Flushed): user_id=%s wallet_id=%s", user_id, locked_wallet.id)

        return transaction

    # ==========================
    # Transfer Fee
    # ==========================

    @staticmethod
    def transfer_fee(
            db: Session,
            patient_id: int,
            doctor_id: int,
            amount: Decimal,
            appointment_id: Optional[int] = None,
            commit: bool = True
    ) -> Transaction:
        """
        انتقال وجه از بیمار به پزشک با اتمیسیته کامل.
        """
        amount_dec = WalletService._to_decimal(amount)
        WalletService._validate_positive_amount(amount_dec)

        logger.info(
            "Transfer fee requested: patient_id=%s doctor_id=%s amount=%s appointment_id=%s commit=%s",
            patient_id,
            doctor_id,
            amount_dec,
            appointment_id,
            commit
        )

        # ساخت یا دریافت کیف پول‌ها بدون ثبت تراکنش مستقل (اجتناب از کامیت ناخواسته)
        patient_wallet = WalletService.get_or_create_wallet(db=db, user_id=patient_id, commit=commit)

        try:
            doctor_user = (
                db.query(User)
                .filter(User.id == doctor_id)
                .first()
            )
        except Exception as exc:
            logger.exception("Failed to fetch doctor user: doctor_id=%s", doctor_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در بررسی پزشک"
            ) from exc

        if not doctor_user:
            logger.warning("Doctor user not found: doctor_id=%s", doctor_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="پزشک یافت نشد"
            )

        doctor_wallet = WalletService.get_or_create_wallet(db=db, user_id=doctor_id, commit=commit)

        # قفل‌گذاری منظم صعودی برای پیشگیری از Deadlock
        wallets = WalletService._lock_wallets(
            db=db,
            wallet_ids=[patient_wallet.id, doctor_wallet.id]
        )

        wallet_map = {wallet.id: wallet for wallet in wallets}
        locked_patient_wallet = wallet_map[patient_wallet.id]
        locked_doctor_wallet = wallet_map[doctor_wallet.id]

        current_balance = WalletService._to_decimal(locked_patient_wallet.balance)

        if current_balance < amount_dec:
            logger.warning(
                "Insufficient funds: patient_id=%s wallet_id=%s balance=%s amount=%s",
                patient_id,
                locked_patient_wallet.id,
                current_balance,
                amount_dec
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="موجودی کیف پول بیمار کافی نیست"
            )

        tracking_code = f"TRX-{uuid.uuid4().hex[:10].upper()}"

        transaction = Transaction(
            sender_wallet_id=locked_patient_wallet.id,
            receiver_wallet_id=locked_doctor_wallet.id,
            amount=amount_dec,
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.SUCCESS,
            appointment_id=appointment_id,
            tracking_code=tracking_code,
            description=f"پرداخت حق ویزیت برای نوبت موقت" if appointment_id is None else f"پرداخت حق ویزیت برای نوبت شماره {appointment_id}"
        )

        locked_patient_wallet.balance = current_balance - amount_dec
        locked_doctor_wallet.balance = (
                WalletService._to_decimal(locked_doctor_wallet.balance) + amount_dec
        )

        db.add(transaction)

        if commit:
            try:
                db.commit()
                db.refresh(transaction)
                logger.info(
                    "Transfer fee successful (Committed): patient_id=%s doctor_id=%s amount=%s",
                    patient_id,
                    doctor_id,
                    amount_dec
                )
            except Exception as exc:
                db.rollback()
                logger.exception("Transfer fee commit failed: patient_id=%s doctor_id=%s", patient_id, doctor_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="خطا در انتقال وجه"
                ) from exc
        else:
            db.flush()
            logger.info("Transfer fee processed (Flushed): patient_id=%s doctor_id=%s", patient_id, doctor_id)

        return transaction

    # ==========================
    # Wallet History
    # ==========================

    @staticmethod
    def get_wallet_history(
            db: Session,
            user_id: int
    ) -> List[Transaction]:
        try:
            # فقط کیف پول را کوئری می‌زنیم تا بیهوده در متد نمایشی کیف‌پول نسازیم
            wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
            if not wallet:
                return []

            transactions = (
                db.query(Transaction)
                .filter(
                    (Transaction.sender_wallet_id == wallet.id)
                    |
                    (Transaction.receiver_wallet_id == wallet.id)
                )
                .order_by(Transaction.created_at.desc())
                .all()
            )

            return transactions

        except Exception as exc:
            logger.exception("Failed to fetch wallet history: user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در دریافت تاریخچه کیف پول"
            ) from exc

    # ==========================
    # Refund
    # ==========================

    @staticmethod
    def refund(
            db: Session,
            transaction_id: int,
            description: str = "برگشت وجه به بیمار",
            commit: bool = True
    ) -> Transaction:
        """
        بازگردانی وجه تراکنش به صورت امن و غیرقابل بازگشت مجدد.
        """
        logger.info("Refund requested: transaction_id=%s commit=%s", transaction_id, commit)

        try:
            # قفل کردن تراکنش اصلی جهت جلوگیری از ایجاد موازیِ refund روی یک فاکتور
            original_tx = (
                db.query(Transaction)
                .filter(Transaction.id == transaction_id)
                .with_for_update()
                .first()
            )
        except Exception as exc:
            logger.exception("Failed to fetch/lock original transaction: transaction_id=%s", transaction_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در بررسی تراکنش اصلی"
            ) from exc

        if not original_tx:
            logger.warning("Original transaction not found for refund: transaction_id=%s", transaction_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="تراکنش یافت نشد"
            )

        if original_tx.transaction_type != TransactionType.TRANSFER:
            logger.warning(
                "Invalid transaction type for refund: transaction_id=%s type=%s",
                transaction_id,
                original_tx.transaction_type
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فقط تراکنش انتقال قابل بازگشت است"
            )

        # بررسی وجود ریفاند قبلی به صورت ایمن
        existing_refund = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_type == TransactionType.REFUND,
                Transaction.appointment_id == original_tx.appointment_id,
            )
            .first()
        )

        if existing_refund:
            logger.warning(
                "Duplicate refund attempt blocked: original_transaction_id=%s appointment_id=%s",
                transaction_id,
                original_tx.appointment_id
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این تراکنش قبلاً بازگشت وجه شده است"
            )

        # قفل‌گذاری ترتیبی صعودی
        wallets = WalletService._lock_wallets(
            db=db,
            wallet_ids=[
                original_tx.sender_wallet_id,
                original_tx.receiver_wallet_id,
            ]
        )

        wallet_map = {wallet.id: wallet for wallet in wallets}
        patient_wallet = wallet_map[original_tx.sender_wallet_id]
        doctor_wallet = wallet_map[original_tx.receiver_wallet_id]

        amount_to_refund = WalletService._to_decimal(original_tx.amount)
        doctor_balance = WalletService._to_decimal(doctor_wallet.balance)

        if doctor_balance < amount_to_refund:
            logger.warning(
                "Insufficient doctor balance for refund: transaction_id=%s balance=%s refund_amount=%s",
                transaction_id,
                doctor_balance,
                amount_to_refund
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="موجودی پزشک برای برگشت وجه کافی نیست"
            )

        refund_tx = Transaction(
            sender_wallet_id=doctor_wallet.id,
            receiver_wallet_id=patient_wallet.id,
            amount=amount_to_refund,
            transaction_type=TransactionType.REFUND,
            status=TransactionStatus.SUCCESS,
            appointment_id=original_tx.appointment_id,
            tracking_code=f"REF-{uuid.uuid4().hex[:10].upper()}",
            description=description,
        )

        doctor_wallet.balance = doctor_balance - amount_to_refund
        patient_wallet.balance = (
                WalletService._to_decimal(patient_wallet.balance) + amount_to_refund
        )

        db.add(refund_tx)

        if commit:
            try:
                db.commit()
                db.refresh(refund_tx)
                logger.info("Refund successful (Committed): refund_id=%s", refund_tx.id)
            except Exception as exc:
                db.rollback()
                logger.exception("Refund commit failed: transaction_id=%s", transaction_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="خطا در برگشت وجه"
                ) from exc
        else:
            db.flush()
            logger.info("Refund processed (Flushed): transaction_id=%s", transaction_id)

        return refund_tx
