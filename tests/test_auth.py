# Path: tests/test_auth.py

import random
import time

from app.models.doctor import Specialty


def generate_dynamic_credentials():
    """
    تولید اطلاعات هویتی منحصربه‌فرد و معتبر برای جلوگیری از خطای 409 Conflict
    در زمان اجرای مجدد تست‌ها.
    """
    timestamp = str(int(time.time() * 1000))[-5:]
    phone = f"0912{timestamp}{random.randint(10, 99)}"
    email = f"user_{timestamp}@doctime.com"

    # تولید کد ملی معتبر بر اساس الگوریتم چک‌سام ده‌دهی
    base = f"228{random.randint(100000, 999999)}"
    total = sum(int(base[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    check_digit = remainder if remainder < 2 else 11 - remainder
    national_id = f"{base}{check_digit}"

    return phone, email, national_id


def request_otp_code(client, phone_number: str) -> str:
    """
    درخواست ارسال کد OTP و دریافت کد از پاسخ دیباگ جهت استفاده در ثبت‌نام.
    """
    response = client.post("/api/v1/auth/otp/send", json={"phone": phone_number})
    assert response.status_code == 200, f"ارسال OTP ناموفق بود: {response.json()}"
    return response.json().get("code_debug_only", "123456")


def test_register_login_me_flow(client):
    from app.api.dependencies import get_current_user

    phone, email, national_id = generate_dynamic_credentials()
    password = "securepassword123"

    otp_code = request_otp_code(client, phone)

    register_payload = {
        "name": "صادق بلوچ",
        "phone": phone,
        "password": password,
        "national_id": national_id,
        "email": email,
        "role": "patient",
    }
    response = client.post(
        f"/api/v1/auth/register?otp_code={otp_code}",
        json=register_payload,
    )
    assert response.status_code == 201, f"ثبت نام ناموفق بود: {response.json()}"

    login_payload = {"phone": phone, "password": password}
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200, f"لاگین ناموفق بود: {response.json()}"

    login_data = response.json()
    assert "token" in login_data
    access_token = login_data["token"]["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # برداشتن موقت override تستی تا JWT واقعی توسط Dependency واقعی decode شود
    current_user_override = client.app.dependency_overrides.pop(
        get_current_user,
        None,
    )
    try:
        response = client.get("/api/v1/auth/me", headers=headers)
    finally:
        if current_user_override is not None:
            client.app.dependency_overrides[get_current_user] = current_user_override

    assert response.status_code == 200, (
        f"دریافت اطلاعات کاربر ناموفق بود: "
        f"status={response.status_code}, body={response.text}"
    )
    me_data = response.json()
    assert me_data["user"]["phone"] == phone


def test_register_duplicate_phone_fails(client):
    phone, email_1, national_id_1 = generate_dynamic_credentials()
    _, email_2, national_id_2 = generate_dynamic_credentials()

    otp_code_1 = request_otp_code(client, phone)
    payload_1 = {
        "name": "کاربر اول",
        "phone": phone,
        "password": "password123",
        "national_id": national_id_1,
        "role": "patient",
    }
    response = client.post(
        f"/api/v1/auth/register?otp_code={otp_code_1}",
        json=payload_1,
    )
    assert response.status_code == 201, f"ثبت نام کاربر اول ناموفق بود: {response.json()}"

    otp_code_2 = request_otp_code(client, phone)
    payload_2 = {
        "name": "کاربر دوم",
        "phone": phone,
        "password": "password123",
        "national_id": national_id_2,
        "role": "patient",
    }
    response = client.post(
        f"/api/v1/auth/register?otp_code={otp_code_2}",
        json=payload_2,
    )
    assert response.status_code == 409


def test_register_duplicate_email_fails(client):
    phone_1, email, national_id_1 = generate_dynamic_credentials()
    phone_2, _, national_id_2 = generate_dynamic_credentials()

    otp_code_1 = request_otp_code(client, phone_1)
    payload_1 = {
        "name": "کاربر اول",
        "phone": phone_1,
        "password": "password123",
        "national_id": national_id_1,
        "email": email,
        "role": "patient",
    }
    response = client.post(
        f"/api/v1/auth/register?otp_code={otp_code_1}",
        json=payload_1,
    )
    assert response.status_code == 201, f"ثبت نام کاربر اول ناموفق بود: {response.json()}"

    otp_code_2 = request_otp_code(client, phone_2)
    payload_2 = {
        "name": "کاربر دوم",
        "phone": phone_2,
        "password": "password123",
        "national_id": national_id_2,
        "email": email,
        "role": "patient",
    }
    response = client.post(
        f"/api/v1/auth/register?otp_code={otp_code_2}",
        json=payload_2,
    )
    assert response.status_code == 409


def test_login_with_wrong_password_fails(client):
    phone, _, national_id = generate_dynamic_credentials()
    password = "correctpassword"

    otp_code = request_otp_code(client, phone)
    payload = {
        "name": "کاربر تست",
        "phone": phone,
        "password": password,
        "national_id": national_id,
        "role": "patient",
    }
    response = client.post(
        f"/api/v1/auth/register?otp_code={otp_code}",
        json=payload,
    )
    assert response.status_code == 201, f"ثبت نام کاربر تست ناموفق بود: {response.json()}"

    login_payload = {"phone": phone, "password": "wrongpassword"}
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401


def test_me_without_token_fails(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_register_doctor_with_valid_specialty(client, db_session):
    """
    پزشک باید با همان specialty_id انتخاب‌شده ثبت شود.
    """
    specialty = Specialty(name="قلب و عروق", slug="cardiology")
    db_session.add(specialty)
    db_session.commit()
    db_session.refresh(specialty)

    phone, email, national_id = generate_dynamic_credentials()
    otp_code = request_otp_code(client, phone)

    doctor_payload = {
        "name": "دکتر صادق بلوچ",
        "phone": phone,
        "password": "doctorpassword123",
        "national_id": national_id,
        "email": email,
        "role": "doctor",
        "medical_council_number": str(random.randint(100000, 999999)),
        "specialty_id": specialty.id,
        "province": "تهران",
        "city": "تهران",
        "address": "خیابان ولیعصر، ساختمان پزشکان سلامت، طبقه سوم",
        "work_shift": "morning",
        "work_days": ["شنبه", "دوشنبه", "چهارشنبه"],
        "morning_start": "08:00",
        "morning_end": "12:00",
    }

    response = client.post(
        f"/api/v1/auth/register?otp_code={otp_code}",
        json=doctor_payload,
    )
    assert response.status_code == 201, f"ثبت نام پزشک ناموفق بود: {response.json()}"

    user_data = response.json()["user"]
    assert user_data["role"] == "doctor"
    assert user_data["specialty"] == "قلب و عروق"
    assert user_data["specialty_id"] == specialty.id
