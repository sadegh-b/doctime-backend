# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database.base import Base, engine as prod_engine
from app.main import app

# تلاش برای ایمپورت کردن get_db از مسیرهای احتمالی پروژه شما
try:
    # مسیر اول احتمالی
    from app.database.base import get_db
except ImportError:
    try:
        # مسیر دوم احتمالی
        from app.database.session import get_db
    except ImportError:
        try:
            # مسیر سوم احتمالی
            from app.deps import get_db
        except ImportError:
            # مسیر چهارم احتمالی (داخل خود main)
            from app.main import get_db

# استفاده از دیتابیس موقت برای تست‌ها تا دیتابیس اصلی شما دستکاری نشود
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    # ساخت تمام جداول قبل از هر تست
    Base.metadata.create_all(bind=engine)
    yield
    # حذف تمام جداول پس از اتمام تست برای تمیز ماندن محیط
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    # جایگزین کردن دیتابیس اصلی با دیتابیس مخصوص تست در FastAPI
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
