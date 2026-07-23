# app/seed_test_data.py

import sys
import os
from datetime import datetime, timedelta, time  # ایمپورت کردن کلاس time

# اضافه کردن مسیر ریشه پروژه به sys.path برای اجرا بدون مشکل ایمپورت
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.base import SessionLocal, engine, Base
from app.models.user import User
from app.models.doctor import Doctor, Specialty
from app.models.availability import Availability
from app.core.security import hash_password


def seed_data():
    db = SessionLocal()
    try:
        print("Dropping all existing tables to avoid schema mismatch...")
        # حذف تمامی جداول قدیمی برای اعمال ساختار جدید بدون باگ
        Base.metadata.drop_all(bind=engine)

        print("Creating database tables with new schema...")
        # ساخت مجدد تمام جداول با ستون‌های جدید (از جمله specialty_id)
        Base.metadata.create_all(bind=engine)

        # 1. ساخت یا واکشی تخصص‌های پایه (Specialties)
        print("Seeding specialties table...")
        default_specialties = [
            {"name": "داخلی", "slug": "internal-medicine", "description": "متخصص بیماری‌های داخلی"},
            {"name": "قلب و عروق", "slug": "cardiology", "description": "متخصص قلب و عروق"},
            {"name": "پوست و مو", "slug": "dermatology", "description": "متخصص پوست، مو و زیبایی"},
            {"name": "اطفال", "slug": "pediatrics", "description": "متخصص بیماری‌های کودکان و نوزادان"},
        ]

        for spec_data in default_specialties:
            existing_spec = db.query(Specialty).filter(Specialty.slug == spec_data["slug"]).first()
            if not existing_spec:
                new_spec = Specialty(
                    name=spec_data["name"],
                    slug=spec_data["slug"],
                    description=spec_data["description"]
                )
                db.add(new_spec)
        db.commit()

        # واکشی تخصص داخلی برای استفاده در ساخت پروفایل پزشک
        internal_medicine_spec = db.query(Specialty).filter(Specialty.slug == "internal-medicine").first()
        if not internal_medicine_spec:
            raise Exception("Failed to seed or fetch internal-medicine specialty.")

        # 2. ساخت کاربر پزشک در جدول users
        print("Creating doctor user...")
        doctor_user = User(
            email="doctor@doctime.com",
            hashed_password=hash_password("doctor123"),
            name="doctor_ali",
            first_name="علی",
            last_name="علوی",
            national_id="1234567890",  # کد ملی ۱۰ رقمی یکتا
            phone="09120000000",  # شماره موبایل
            role="doctor",
            is_active=True
        )
        db.add(doctor_user)
        db.commit()
        db.refresh(doctor_user)

        # 3. ثبت اطلاعات تخصصی پزشک در جدول doctors
        print("Creating doctor profile...")
        doctor_profile = Doctor(
            user_id=doctor_user.id,
            medical_council_number="12345",  # شماره نظام پزشکی (اجباری و یکتا)
            specialty_id=internal_medicine_spec.id,  # اتصال کلید خارجی به تخصص ایجاد شده
            province="سیستان و بلوچستان",  # استان (اجباری)
            city="چابهار",  # شهر (اجباری)
            address="بلوار آزادی، پلاک ۱۲",  # آدرس کلینیک
            bio="متخصص بیماری‌های داخلی با سابقه ۱۰ سال طبابت در چابهار",
            consultation_fee=150000,
            experience_years=10
        )
        db.add(doctor_profile)
        db.commit()
        db.refresh(doctor_profile)

        # 4. ساخت کاربر بیمار در جدول users
        print("Creating patient user...")
        patient_user = User(
            email="patient@doctime.com",
            hashed_password=hash_password("patient123"),
            name="sadegh_baloch",
            first_name="صادق",
            last_name="بلوچ",
            national_id="0987654321",  # کد ملی ۱۰ رقمی یکتا
            phone="09150000000",  # شماره موبایل
            role="patient",
            is_active=True
        )
        db.add(patient_user)
        db.commit()
        db.refresh(patient_user)

        # 5. ایجاد زمان‌های حضور خالی (Availability) برای پزشک
        print("Adding availability slots...")
        today = datetime.now().date()
        slots = [
            {"date": today, "start": time(10, 0), "end": time(10, 30)},
            {"date": today, "start": time(11, 0), "end": time(11, 30)},
            {"date": today + timedelta(days=1), "start": time(16, 0), "end": time(16, 30)}
        ]

        for s in slots:
            availability = Availability(
                doctor_id=doctor_profile.id,
                date=s["date"],
                start_time=s["start"],
                end_time=s["end"],
                is_booked=False
            )
            db.add(availability)

        db.commit()
        print("Database seeded successfully with test doctor, patient, specialties and availability slots!")
        print("-" * 50)
        print("Doctor Login Info:")
        print("  Phone: 09120000000")
        print("  Password: doctor123")
        print("Patient Login Info:")
        print("  Phone: 09150000000")
        print("  Password: patient123")
        print("-" * 50)

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
