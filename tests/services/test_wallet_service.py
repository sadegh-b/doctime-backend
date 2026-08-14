import pytest
from decimal import Decimal

from app.models.user import User
from app.models.wallet import (
    Wallet,
    Transaction,
    TransactionType,
    TransactionStatus,
)
from app.services.wallet_service import WalletService


# =========================================================
# Helpers
# =========================================================

def create_user(db, user_id: int, phone: str = None):
    user = User(
        id=user_id,
        name=f"user-{user_id}",
        first_name="Test",
        last_name="User",
        national_id=f"123456789{user_id}",
        phone=phone or f"091200000{user_id}",
        email=f"user{user_id}@test.com",
        hashed_password="hashed-password",
        role="patient",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# =========================================================
# Tests: _to_decimal / validation
# =========================================================

def test_to_decimal_rounds_half_up():
    assert WalletService._to_decimal("10.005") == Decimal("10.01")
    assert WalletService._to_decimal("10.004") == Decimal("10.00")
    assert WalletService._to_decimal(10) == Decimal("10.00")


def test_validate_positive_amount_rejects_zero():
    with pytest.raises(Exception) as exc:
        WalletService._validate_positive_amount(Decimal("0.00"))
    assert "مبلغ باید بیشتر از صفر باشد" in str(exc.value)


def test_validate_positive_amount_rejects_negative():
    with pytest.raises(Exception) as exc:
        WalletService._validate_positive_amount(Decimal("-1.00"))
    assert "مبلغ باید بیشتر از صفر باشد" in str(exc.value)


# =========================================================
# Tests: get_or_create_wallet
# =========================================================

def test_get_or_create_wallet_creates_wallet(db_session):
    create_user(db_session, user_id=1)

    wallet = WalletService.get_or_create_wallet(
        db=db_session,
        user_id=1,
        commit=True,
    )

    assert wallet.id is not None
    assert wallet.user_id == 1
    assert wallet.balance == Decimal("0.00")
    assert wallet.is_active is True
    assert wallet.is_locked is False


def test_get_or_create_wallet_returns_existing_wallet(db_session):
    create_user(db_session, user_id=1)
    existing = Wallet(
        user_id=1,
        balance=Decimal("500.00"),
        is_active=True,
        is_locked=False,
    )
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    wallet = WalletService.get_or_create_wallet(
        db=db_session,
        user_id=1,
        commit=True,
    )

    assert wallet.id == existing.id
    assert wallet.balance == Decimal("500.00")


# =========================================================
# Tests: deposit
# =========================================================

def test_deposit_increases_balance_and_creates_success_transaction(db_session):
    create_user(db_session, user_id=1)

    transaction = WalletService.deposit(
        db=db_session,
        user_id=1,
        amount=Decimal("1000"),
        description="wallet topup",
        commit=True,
    )

    wallet = db_session.query(Wallet).filter(Wallet.user_id == 1).first()

    assert wallet is not None
    assert wallet.balance == Decimal("1000.00")
    assert transaction.id is not None
    assert transaction.receiver_wallet_id == wallet.id
    assert transaction.sender_wallet_id is None
    assert transaction.amount == Decimal("1000.00")
    assert transaction.transaction_type == TransactionType.DEPOSIT
    assert transaction.status == TransactionStatus.SUCCESS
    assert transaction.description == "wallet topup"
    assert transaction.tracking_code.startswith("DEP-")


def test_deposit_rejects_non_positive_amount(db_session):
    create_user(db_session, user_id=1)

    with pytest.raises(Exception) as exc:
        WalletService.deposit(
            db=db_session,
            user_id=1,
            amount=Decimal("0"),
            commit=True,
        )

    assert "مبلغ باید بیشتر از صفر باشد" in str(exc.value)


def test_deposit_uses_two_decimal_precision(db_session):
    create_user(db_session, user_id=1)

    transaction = WalletService.deposit(
        db=db_session,
        user_id=1,
        amount=Decimal("1000.005"),
        commit=True,
    )

    wallet = db_session.query(Wallet).filter(Wallet.user_id == 1).first()

    assert wallet.balance == Decimal("1000.01")
    assert transaction.amount == Decimal("1000.01")


# =========================================================
# Tests: create_pending_deposit / verify_deposit
# =========================================================

def test_create_pending_deposit_does_not_increase_balance(db_session):
    create_user(db_session, user_id=1)

    transaction = WalletService.create_pending_deposit(
        db=db_session,
        user_id=1,
        amount=Decimal("2000"),
    )

    wallet = db_session.query(Wallet).filter(Wallet.user_id == 1).first()

    assert wallet.balance == Decimal("0.00")
    assert transaction.status == TransactionStatus.PENDING
    assert transaction.transaction_type == TransactionType.DEPOSIT
    assert transaction.receiver_wallet_id == wallet.id
    assert transaction.tracking_code.startswith("DEP-")


def test_verify_deposit_success_is_idempotent(db_session):
    create_user(db_session, user_id=1)

    pending = WalletService.create_pending_deposit(
        db=db_session,
        user_id=1,
        amount=Decimal("1500"),
    )

    first = WalletService.verify_deposit(
        db=db_session,
        authority=pending.tracking_code,
        is_bank_successful=True,
    )

    wallet = db_session.query(Wallet).filter(Wallet.user_id == 1).first()
    assert first.status == TransactionStatus.SUCCESS
    assert wallet.balance == Decimal("1500.00")

    second = WalletService.verify_deposit(
        db=db_session,
        authority=pending.tracking_code,
        is_bank_successful=True,
    )

    wallet_after = db_session.query(Wallet).filter(Wallet.user_id == 1).first()
    assert second.id == first.id
    assert second.status == TransactionStatus.SUCCESS
    assert wallet_after.balance == Decimal("1500.00")


def test_verify_deposit_failure_marks_transaction_failed(db_session):
    create_user(db_session, user_id=1)

    pending = WalletService.create_pending_deposit(
        db=db_session,
        user_id=1,
        amount=Decimal("1500"),
    )

    result = WalletService.verify_deposit(
        db=db_session,
        authority=pending.tracking_code,
        is_bank_successful=False,
    )

    wallet = db_session.query(Wallet).filter(Wallet.user_id == 1).first()

    assert result.status == TransactionStatus.FAILED
    assert wallet.balance == Decimal("0.00")


def test_verify_deposit_unknown_authority_returns_404(db_session):
    with pytest.raises(Exception) as exc:
        WalletService.verify_deposit(
            db=db_session,
            authority="DEP-NOT-FOUND",
            is_bank_successful=True,
        )

    assert "تراکنش یافت نشد" in str(exc.value)


# =========================================================
# Tests: transfer_fee
# =========================================================

def test_transfer_fee_moves_balance_between_wallets(db_session):
    create_user(db_session, user_id=1)
    create_user(db_session, user_id=2)

    WalletService.deposit(
        db=db_session,
        user_id=1,
        amount=Decimal("3000"),
        commit=True,
    )

    transaction = WalletService.transfer_fee(
        db=db_session,
        patient_id=1,
        doctor_id=2,
        amount=Decimal("1200"),
        appointment_id=55,
        commit=True,
    )

    patient_wallet = db_session.query(Wallet).filter(Wallet.user_id == 1).first()
    doctor_wallet = db_session.query(Wallet).filter(Wallet.user_id == 2).first()

    assert patient_wallet.balance == Decimal("1800.00")
    assert doctor_wallet.balance == Decimal("1200.00")
    assert transaction.transaction_type == TransactionType.TRANSFER
    assert transaction.status == TransactionStatus.SUCCESS
    assert transaction.amount == Decimal("1200.00")
    assert transaction.sender_wallet_id == patient_wallet.id
    assert transaction.receiver_wallet_id == doctor_wallet.id
    assert transaction.appointment_id == 55
    assert transaction.tracking_code.startswith("TRX-")


def test_transfer_fee_rejects_insufficient_balance(db_session):
    create_user(db_session, user_id=1)
    create_user(db_session, user_id=2)

    with pytest.raises(Exception) as exc:
        WalletService.transfer_fee(
            db=db_session,
            patient_id=1,
            doctor_id=2,
            amount=Decimal("1200"),
            commit=True,
        )

    assert "موجودی کیف پول بیمار کافی نیست" in str(exc.value)


# =========================================================
# Tests: refund
# =========================================================

def test_refund_returns_money_and_creates_refund_transaction(db_session):
    create_user(db_session, user_id=1)
    create_user(db_session, user_id=2)

    WalletService.deposit(
        db=db_session,
        user_id=1,
        amount=Decimal("3000"),
        commit=True,
    )

    original = WalletService.transfer_fee(
        db=db_session,
        patient_id=1,
        doctor_id=2,
        amount=Decimal("1000"),
        appointment_id=100,
        commit=True,
    )

    refund_tx = WalletService.refund(
        db=db_session,
        transaction_id=original.id,
        commit=True,
    )

    patient_wallet = db_session.query(Wallet).filter(Wallet.user_id == 1).first()
    doctor_wallet = db_session.query(Wallet).filter(Wallet.user_id == 2).first()

    assert patient_wallet.balance == Decimal("3000.00")
    assert doctor_wallet.balance == Decimal("0.00")
    assert refund_tx.transaction_type == TransactionType.REFUND
    assert refund_tx.status == TransactionStatus.SUCCESS
    assert refund_tx.amount == Decimal("1000.00")
    assert refund_tx.sender_wallet_id == doctor_wallet.id
    assert refund_tx.receiver_wallet_id == patient_wallet.id


def test_refund_rejects_duplicate_refund_for_same_appointment(db_session):
    create_user(db_session, user_id=1)
    create_user(db_session, user_id=2)

    WalletService.deposit(
        db=db_session,
        user_id=1,
        amount=Decimal("3000"),
        commit=True,
    )

    original = WalletService.transfer_fee(
        db=db_session,
        patient_id=1,
        doctor_id=2,
        amount=Decimal("1000"),
        appointment_id=100,
        commit=True,
    )

    WalletService.refund(
        db=db_session,
        transaction_id=original.id,
        commit=True,
    )

    with pytest.raises(Exception) as exc:
        WalletService.refund(
            db=db_session,
            transaction_id=original.id,
            commit=True,
        )

    assert "قبلاً برگشت داده شده است" in str(exc.value)


# =========================================================
# Tests: history
# =========================================================

def test_get_wallet_history_returns_transactions(db_session):
    create_user(db_session, user_id=1)
    create_user(db_session, user_id=2)

    WalletService.deposit(
        db=db_session,
        user_id=1,
        amount=Decimal("2000"),
        commit=True,
    )

    history = WalletService.get_wallet_history(
        db=db_session,
        user_id=1,
    )

    assert len(history) == 1
    assert history[0].transaction_type == TransactionType.DEPOSIT


def test_get_wallet_history_returns_empty_list_for_missing_wallet(db_session):
    history = WalletService.get_wallet_history(
        db=db_session,
        user_id=999,
    )

    assert history == []
