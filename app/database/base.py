# app/database/base.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. خواندن آدرس دیتابیس از متغیرهای محیطی (برای امنیت و پایداری در Render)
# اگر متغیری پیدا نکند، به صورت پیش‌فرض از همان SQLite محلی استفاده می‌کند
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./doctime.db")

# 2. مدیریت پارامترهای اتصال (SQLite به check_same_thread نیاز دارد، بقیه نه)
connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# 3. ایجاد موتور دیتابیس
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args
)

# ایجاد کلاس Session برای کار با دیتابیس
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# کلاس پایه برای مدل‌های ORM
Base = declarative_base()

# Dependency برای استفاده در Routeها
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
