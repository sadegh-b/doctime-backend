# Path: backend/app/core/logging_config.py

import logging
import sys
from pathlib import Path

# ایجاد پوشه logs در ریشه پروژه در صورت عدم وجود
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "doctime.log"

# فرمت نمایش لاگ‌ها
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging() -> None:
    """تنظیمات پایه سیستم لاگینگ پروژه Doctime"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # جلوگیری از اضافه شدن چندباره هندلرها در بارگذاری مجدد
    if logger.hasHandlers():
        logger.handlers.clear()

    # ۱. هندلر برای نوشتن لاگ‌ها در ترمینال (Standard Output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # ۲. هندلر برای ذخیره لاگ‌ها در فایل با انکودینگ UTF-8 برای پشتیبانی از فارسی
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.setLevel(logging.WARNING)  # فقط خطاها و هشدارهای مهم در فایل ذخیره شوند
    logger.addHandler(file_handler)

    logging.info("Logging system initialized successfully.")
