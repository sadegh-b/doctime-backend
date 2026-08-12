from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# ——— تنظیمات مخصوص SQLite (فقط dev) ———
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# ——— موتور با مدیریت pool برای Production ———
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,      # قبل از استفاده، زنده بودن اتصال را تست می‌کند
    pool_recycle=300,        # اتصال‌های بالای ۵ دقیقه را بازیافت می‌کند (ضد stale)
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,         # تا ۳۰ ثانیه منتظر اتصال آزاد می‌ماند
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

def get_db():
    """Dependency FastAPI — هر request یک Session تازه و ایزوله می‌گیرد."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
