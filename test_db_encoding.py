# Path: test_db_encoding.py

import sys
from app.database import SessionLocal
from app.models.doctor import Specialty

# تنظیم خروجی استاندارد ترمینال روی UTF-8 در پایتون
sys.stdout.reconfigure(encoding='utf-8')

def check_specialties():
    db = SessionLocal()
    try:
        specialties = db.query(Specialty).all()
        print(f"Total specialties found: {len(specialties)}")
        for spec in specialties:
            # چاپ شناسه و نام دقیق به همراه بایت‌های آن برای بررسی خراب بودن یا نبودن کاراکترها
            raw_bytes = spec.name.encode('utf-8', errors='replace')
            print(f"ID: {spec.id} | Name: {spec.name} | Bytes: {raw_bytes}")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_specialties()
