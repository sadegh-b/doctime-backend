# Path: tests/test_appointments.py

import pytest
from fastapi import status
from decimal import Decimal
from datetime import date, time
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.doctor import Doctor, Specialty
from app.models.availability import Availability
from app.models.wallet import Transaction, TransactionType, TransactionStatus
from app.services.wallet_service import WalletService


@pytest.fixture
def create_test_users(db_session: Session):
    """ایجاد بیمار و پزشک تست به همراه کیف پول‌های پایه برای تست تراکنش‌ها"""
    # ۱. ایجاد تخصص پایه با فیلد slug
    specialty = Specialty(name="عمومی", slug="general")
    db_session.add(specialty)
    db_session.commit()
    db_session.refresh(specialty)

    # ۲. ایجاد کاربر بیمار با فیلدهای نام و نام‌خانوادگی کامل
    patient_user = User(
        name="صادق بیمار",
        first_name="صادق",
        last_name="بیمار",
        email="sadegh_patient@example.com",
        phone="09123456789",
        role="patient",
        hashed_password="fakehashedpassword"
    )
    db_session.add(patient_user)

    # ۳. ایجاد کاربر پزشک
    doctor_user = User(
        name="دکتر صادق",
        first_name="دکتر",
        last_name="صادق",
        email="sadegh_doctor@example.com",
        phone="09987654321",
        role="doctor",
        hashed_password="fakehashedpassword"
    )
    db_session.add(doctor_user)
    db_session.commit()
    db_session.refresh(patient_user)
    db_session.refresh(doctor_user)

    # ۴. ایجاد پروفایل پزشک با انتساب به شناسه تخصص ایجادشده و پر کردن تمامی فیلدهای اجباری
    doctor_profile = Doctor(
        user_id=doctor_user.id,
        specialty_id=specialty.id,
        consultation_fee=150000.00,  # ۱۵۰,۰۰۰ تومان
        medical_council_number="654321",  # شماره نظام پزشکی یکتا برای جلوگیری از تداخل UNIQUE
        province="تهران",
        city="تهران",
        address="تهران، خیابان ولیعصر",
        experience_years=5,
        work_shift="morning"
    )
    db_session.add(doctor_profile)
    db_session.commit()
    db_session.refresh(doctor_profile)  # گرفتن شناسه تولید شده doctor_profile.id

    # ۵. مقداردهی اولیه به کیف‌پول‌ها با موجودی صفر
    WalletService.get_or_create_wallet(db_session, patient_user.id)
    WalletService.get_or_create_wallet(db_session, doctor_user.id)
    db_session.commit()

    return {
        "patient": patient_user,
        "doctor_user": doctor_user,
        "doctor_profile": doctor_profile
    }


@pytest.fixture
def create_availability_slot(db_session: Session, create_test_users):
    """ایجاد یک زمان خالی و در دسترس برای رزرو نوبت تست"""
    doctor_profile = create_test_users["doctor_profile"]

    # استفاده از شناسه واقعی و Commit شده پزشک
    slot = Availability(
        doctor_id=doctor_profile.id,
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(10, 30),
        is_available=True,
        is_booked=False
    )
    db_session.add(slot)
    db_session.commit()
    db_session.refresh(slot)
    return slot


def mock_get_current_user_as_patient(user):
    def _override():
        return user
    return _override


def test_booking_fails_due_to_insufficient_funds(
    client: TestClient,
    db_session: Session,
    create_test_users,
    create_availability_slot
):
    """تست خطای رزرو نوبت در زمان ناکافی بودن موجودی کیف پول بیمار"""
    patient = create_test_users["patient"]
    slot = create_availability_slot

    # تنظیم مجدد موجودی بیمار روی 0
    patient_wallet = WalletService.get_or_create_wallet(db_session, patient.id)
    patient_wallet.balance = 0.0
    db_session.commit()

    # شبیه‌سازی ورود به عنوان بیمار
    from app.api.dependencies import get_current_user
    client.app.dependency_overrides[get_current_user] = mock_get_current_user_as_patient(patient)

    # ارسال درخواست رزرو
    response = client.post(
        "/api/v1/appointments",
        json={"availability_id": slot.id, "notes": "نیاز به مشاوره سریع"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "موجودی کیف پول بیمار کافی نیست" in response.json()["detail"]

    # اطمینان از اینکه اسلات قفل نشده است
    db_session.refresh(slot)
    assert slot.is_booked is False
    assert slot.is_available is True


def test_successful_booking_and_wallet_transfer(
    client: TestClient,
    db_session: Session,
    create_test_users,
    create_availability_slot
):
    """تست رزرو موفقیت‌آمیز نوبت با کسر هزینه از بیمار و واریز به پزشک"""
    patient = create_test_users["patient"]
    doctor_user = create_test_users["doctor_user"]
    slot = create_availability_slot
    fee = create_test_users["doctor_profile"].consultation_fee

    # شارژ کیف پول بیمار به میزان مورد نیاز
    WalletService.deposit(db_session, patient.id, Decimal(str(fee)), "شارژ تست")

    from app.api.dependencies import get_current_user
    client.app.dependency_overrides[get_current_user] = mock_get_current_user_as_patient(patient)

    response = client.post(
        "/api/v1/appointments",
        json={"availability_id": slot.id, "notes": "نوبت با پرداخت مالی"}
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert "appointment_id" in data

    # اعتبارسنجی تغییرات در دیتابیس
    db_session.expire_all()

    patient_wallet = WalletService.get_or_create_wallet(db_session, patient.id)
    doctor_wallet = WalletService.get_or_create_wallet(db_session, doctor_user.id)

    # موجودی باید به درستی جابجا شده باشد
    assert patient_wallet.balance == 0.0
    assert doctor_wallet.balance == float(fee)

    # بررسی ثبت تراکنش مالی با لینک درست به نوبت
    tx = db_session.query(Transaction).filter(
        Transaction.appointment_id == data["appointment_id"]
    ).first()

    assert tx is not None
    assert tx.transaction_type == TransactionType.TRANSFER
    assert tx.status == TransactionStatus.SUCCESS
    assert tx.amount == Decimal(str(fee))


def test_cancel_appointment_and_refund_flow(
    client: TestClient,
    db_session: Session,
    create_test_users,
    create_availability_slot
):
    """تست لغو نوبت و بازگشت خودکار وجه از حساب پزشک به بیمار"""
    patient = create_test_users["patient"]
    doctor_user = create_test_users["doctor_user"]
    slot = create_availability_slot
    fee = create_test_users["doctor_profile"].consultation_fee

    # ۱. رزرو نوبت اولیه
    WalletService.deposit(db_session, patient.id, Decimal(str(fee)), "شارژ جهت تست ریفاند")

    from app.api.dependencies import get_current_user
    client.app.dependency_overrides[get_current_user] = mock_get_current_user_as_patient(patient)

    booking_resp = client.post(
        "/api/v1/appointments",
        json={"availability_id": slot.id, "notes": "نوبت جهت لغو"}
    )
    appointment_id = booking_resp.json()["appointment_id"]

    # بررسی موجودی قبل از لغو
    db_session.expire_all()
    patient_wallet = WalletService.get_or_create_wallet(db_session, patient.id)
    doctor_wallet = WalletService.get_or_create_wallet(db_session, doctor_user.id)
    assert patient_wallet.balance == 0.0
    assert doctor_wallet.balance == float(fee)

    # ۲. لغو نوبت توسط بیمار
    cancel_resp = client.post(f"/api/v1/appointments/{appointment_id}/cancel")
    assert cancel_resp.status_code == status.HTTP_200_OK
    assert cancel_resp.json()["success"] is True

    # ۳. بررسی بازگشت پول در دیتابیس
    db_session.expire_all()
    assert patient_wallet.balance == float(fee)
    assert doctor_wallet.balance == 0.0

    # بررسی ثبت تراکنش REFUND
    refund_tx = db_session.query(Transaction).filter(
        Transaction.appointment_id == appointment_id,
        Transaction.transaction_type == TransactionType.REFUND
    ).first()

    assert refund_tx is not None
    assert refund_tx.amount == Decimal(str(fee))
    assert refund_tx.sender_wallet_id == doctor_wallet.id
    assert refund_tx.receiver_wallet_id == patient_wallet.id
