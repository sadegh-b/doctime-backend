import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.session import get_db
from app.main import app

from app.models.user import User
from app.models.doctor import Doctor, Specialty

from app.core.security import create_access_token

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(
    db_session,
    *,
    name: str,
    first_name: str,
    last_name: str,
    phone: str,
    role: str,
) -> User:
    user = User(
        name=name,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role=role,
        is_active=True,
        hashed_password="fake_hashed_password",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_specialty(db_session) -> Specialty:
    specialty = Specialty(
        name="General Medicine",
        slug="general-medicine",
        description="Test specialty",
    )
    db_session.add(specialty)
    db_session.commit()
    db_session.refresh(specialty)
    return specialty


@pytest.fixture(scope="function")
def doctor_token_headers(db_session):
    specialty = _create_specialty(db_session)

    doctor_user = _create_user(
        db_session,
        name="Test Doctor",
        first_name="Test",
        last_name="Doctor",
        phone="09120000001",
        role="doctor",
    )

    doctor_profile = Doctor(
        user_id=doctor_user.id,
        specialty_id=specialty.id,
        city="Tehran",
        experience_years=5,
        consultation_fee=100000,
        work_shift="morning",
        province="Tehran",
        address="Test Address",
    )
    db_session.add(doctor_profile)
    db_session.commit()
    db_session.refresh(doctor_profile)

    token = create_access_token(subject=str(doctor_user.id))

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def patient_token_headers(db_session):
    patient_user = _create_user(
        db_session,
        name="Test Patient",
        first_name="Test",
        last_name="Patient",
        phone="09120000002",
        role="patient",
    )

    token = create_access_token(subject=str(patient_user.id))

    return {"Authorization": f"Bearer {token}"}
