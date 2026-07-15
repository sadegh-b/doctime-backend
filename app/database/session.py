# app/database/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

connect_args = {}
# تنظیمات خاص برای دیتابیس SQLite جهت مدیریت تردها
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# تابع ژنراتور برای مدیریت چرخه عمر نشست دیتابیس
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
