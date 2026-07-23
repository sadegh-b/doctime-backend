# Path: tests/test_auth.py

import pytest
import random
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def generate_dynamic_credentials():
    """
    تولید اطلاعات هویتی منحصر‌به‌فرد و معتبر برای جلوگیری از خطای 409 Conflict در زمان اجرای مجدد تست‌ها.
    طول شماره تلفن خروجی دقیقاً ۱۱ رقم خواهد بود.
    """
    # گرفتن ۵ رقم آخر زمان حال
    timestamp = str(int(time.time() * 1000))[-5:]
    # 0912 (۴ رقم) + timestamp (۵ رقم) + عدد تصادفی دو رقمی (۲ رقم) = ۱۱ رقم
    phone = f"0912{timestamp}{random.randint(10, 99)}"
    email = f"user_{timestamp}@doctime.com"

    # تولید کد ملی معتبر بر اساس الگوریتم چکسام دهدهی
    base = f"228{random.randint(100000, 999999)}"
    total = sum(int(base[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    if remainder < 2:
        check_digit = remainder
    else:
        check_digit = 11 - remainder
    national_id = f"{base}{check_digit}"

    return phone, email, national_id


def test_register_login_me_flow():
    phone, email, national_id = generate_dynamic_credentials()
    password = "securepassword123"

    register_payload = {
        "name": "صادق بلوچ",
        "phone": phone,
        "password": password,
        "national_id": national_id,
        "email": email,
        "role": "patient"
    }

    response = client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == 201, f"ثبت نام ناموفق بود: {response.json()}"

    login_payload = {
        "phone": phone,
        "password": password
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200, f"لاگین ناموفق بود: {response.json()}"

    login_data = response.json()
    assert "token" in login_data
    access_token = login_data["token"]["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    me_data = response.json()
    assert me_data["user"]["phone"] == phone


def test_register_duplicate_phone_fails():
    phone, email_1, national_id_1 = generate_dynamic_credentials()
    _, email_2, national_id_2 = generate_dynamic_credentials()

    payload_1 = {
        "name": "کاربر اول",
        "phone": phone,
        "password": "password123",
        "national_id": national_id_1,
        "role": "patient"
    }
    response = client.post("/api/v1/auth/register", json=payload_1)
    assert response.status_code == 201, f"ثبت نام کاربر اول ناموفق بود: {response.json()}"

    payload_2 = {
        "name": "کاربر دوم",
        "phone": phone,
        "password": "password123",
        "national_id": national_id_2,
        "role": "patient"
    }
    response = client.post("/api/v1/auth/register", json=payload_2)
    assert response.status_code == 409


def test_register_duplicate_email_fails():
    phone_1, email, national_id_1 = generate_dynamic_credentials()
    phone_2, _, national_id_2 = generate_dynamic_credentials()

    payload_1 = {
        "name": "کاربر اول",
        "phone": phone_1,
        "password": "password123",
        "national_id": national_id_1,
        "email": email,
        "role": "patient"
    }
    response = client.post("/api/v1/auth/register", json=payload_1)
    assert response.status_code == 201, f"ثبت نام کاربر اول ناموفق بود: {response.json()}"

    payload_2 = {
        "name": "کاربر دوم",
        "phone": phone_2,
        "password": "password123",
        "national_id": national_id_2,
        "email": email,
        "role": "patient"
    }
    response = client.post("/api/v1/auth/register", json=payload_2)
    assert response.status_code == 409


def test_login_with_wrong_password_fails():
    phone, _, national_id = generate_dynamic_credentials()
    password = "correctpassword"

    payload = {
        "name": "کاربر تست",
        "phone": phone,
        "password": password,
        "national_id": national_id,
        "role": "patient"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, f"ثبت نام کاربر تست ناموفق بود: {response.json()}"

    login_payload = {
        "phone": phone,
        "password": "wrongpassword"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401


def test_me_without_token_fails():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_register_doctor_with_valid_specialty():
    phone, _, national_id = generate_dynamic_credentials()

    doctor_payload = {
        "name": "دکتر صادق بلوچ",
        "phone": phone,
        "password": "doctorpassword123",
        "national_id": national_id,
        "role": "doctor",

        "medical_council_number": str(random.randint(100000, 999999)),
        "specialty": "قلب و عروق",
        "province": "تهران",
        "city": "تهران",
        "address": "خیابان ولیعصر، ساختمان پزشکان سلامت، طبقه سوم",

        "work_shift": "morning",
        "work_days": ["شنبه", "دوشنبه", "چهارشنبه"],
        "morning_start": "08:00",
        "morning_end": "12:00"
    }

    response = client.post("/api/v1/auth/register", json=doctor_payload)
    assert response.status_code == 201, f"ثبت نام پزشک ناموفق بود: {response.json()}"

    response_data = response.json()
    user_data = response_data.get("user", {})
    assert user_data.get("role") == "doctor"
    assert user_data.get("specialty") == "قلب و عروق"
