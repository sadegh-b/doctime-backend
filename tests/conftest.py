import sys
from pathlib import Path
from typing import Optional

import pytest
from fastapi import Depends, Header, HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# تنظیم مسیر پروژه
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- وارد کردن مدل‌ها به صورت صریح برای ثبت در Metadata ---
from app.database.base import Base  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.doctor import Doctor, Specialty  # noqa: E402
from app.models.otp import OTPVerification  # noqa: E402


@pytest.fixture(scope="function")
def db_session():
    # استفاده از StaticPool برای پایداری در SQLite in-memory
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine,
    )

    # اطمینان از وجود جدول OTP در متادیتا قبل از ساخت
    assert "otp_verifications" in Base.metadata.tables, "OTP model not registered!"

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def test_user(db_session):
    user = User(
        name="Test Patient",
        first_name="Test",
        last_name="Patient",
        national_id="0013547890",
        phone="09120000000",
        email="test.patient@example.com",
        hashed_password="test-hashed-password",
        role="patient",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_doctor(db_session):
    specialty = Specialty(name="داخلی", slug="internal-test")
    db_session.add(specialty)
    db_session.flush()

    user = User(
        name="Test Doctor",
        first_name="Test",
        last_name="Doctor",
        national_id="0013547891",
        phone="09120000001",
        email="test.doctor@example.com",
        hashed_password="test-hashed-password",
        role="doctor",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    doctor = Doctor(
        user_id=user.id,
        medical_council_number="123456",
        specialty_id=specialty.id,
        province="تهران",
        city="تهران",
        address="test address",
        work_shift="morning",
    )
    db_session.add(doctor)
    db_session.commit()

    db_session.refresh(user)
    db_session.refresh(doctor)
    return user


@pytest.fixture(scope="function")
def test_app(db_session, test_user, test_doctor):
    from app.api.dependencies import get_current_doctor, get_current_user
    from app.database.session import get_db
    from app.main import app
    from app.models.user import User

    def override_get_db():
        yield db_session

    def override_get_current_user(
        authorization: Optional[str] = Header(default=None),
    ):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization.removeprefix("Bearer ").strip()

        # منطق توکن‌های تستی
        if token == "doctor-token":
            user = db_session.query(User).filter(User.role == "doctor").first()
            if not user:
                raise HTTPException(status_code=401, detail="Doctor not found")
            return user

        if token == "patient-token":
            user = db_session.query(User).filter(User.role == "patient").first()
            if not user:
                raise HTTPException(status_code=401, detail="Patient not found")
            return user

        # اجازه دادن به JWT واقعی برای تست‌های جریان کامل
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Test override: valid token required",
        )

    def override_get_current_doctor(current_user=Depends(get_current_user)):
        # هندل کردن Enum یا String برای نقش
        role = getattr(current_user.role, "value", current_user.role)
        if role != "doctor":
            raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

        doctor = db_session.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="پروفایل پزشک یافت نشد.")
        return doctor

    # اعمال Overrideها
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_doctor] = override_get_current_doctor

    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(test_app):
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def doctor_token_headers(test_doctor):
    return {"Authorization": "Bearer doctor-token"}


@pytest.fixture(scope="function")
def patient_token_headers(test_user):
    return {"Authorization": "Bearer patient-token"}
