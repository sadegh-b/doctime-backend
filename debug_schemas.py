# C:\PythonProject\PythonProject\doctime-backend-clean\debug_schemas.py
import os
from pydantic import ValidationError

# ۱. خواندن و چاپ کدهای فایل schemas/user.py
print("=== 1. Content of app/schemas/user.py ===")
schema_path = os.path.join("app", "schemas", "user.py")
if os.path.exists(schema_path):
    with open(schema_path, "r", encoding="utf-8") as f:
        print(f.read())
else:
    print(f"File not found at: {schema_path}")

print("\n" + "=" * 50 + "\n")

# ۲. تست فرآیند اعتبارسنجی (Validation)
print("=== 2. Testing Pydantic UserRegister Validation ===")
try:
    from app.schemas.user import UserRegister

    # الف) تست ثبت‌نام بیمار (بدون کد ملی)
    patient_data = {
        "phone": "09123456789",
        "password": "Password123!",
        "name": "صادق بیمار",
        "first_name": "صادق",
        "last_name": "بیمار",
        "role": "patient"
    }
    print("Running Patient validation test...")
    try:
        user = UserRegister(**patient_data)
        print("✅ Patient validation PASSED!")
    except ValidationError as e:
        print("❌ Patient validation FAILED!")
        print(e)

    print("-" * 50)

    # ب) تست ثبت‌نام پزشک (با کد ملی و تخصص)
    doctor_data = {
        "phone": "09129876543",
        "password": "Password123!",
        "name": "دکتر صادق",
        "first_name": "صادق",
        "last_name": "پزشک",
        "role": "doctor",
        "national_id": "1234567890",
        "specialty": "Cardiology"
    }
    print("Running Doctor validation test...")
    try:
        user = UserRegister(**doctor_data)
        print("✅ Doctor validation PASSED!")
    except ValidationError as e:
        print("❌ Doctor validation FAILED!")
        print(e)

except ImportError as e:
    print(f"Import Error: Could not import UserRegister. Detail: {e}")
