# Path: final_api_test.py
import requests
import json

# آدرس لاگین
url = "http://127.0.0.1:8000/api/v1/auth/login"

# اطلاعات ورودی (اطمینان حاصل کن که این کاربر قبلاً ثبت‌نام شده است)
payload = {
    "phone": "09999999999",
    "password": "SecurePassword123"
}

print("--- در حال ارسال درخواست به سرور ---")

try:
    response = requests.post(url, json=payload, timeout=5)

    print(f"Status Code: {response.status_code}")

    # بررسی اینکه آیا پاسخ موفقیت‌آمیز بوده یا خیر
    if response.status_code == 200:
        print("✅ اتصال موفقیت‌آمیز بود.")
        # نمایش پاسخ با فونت فارسی صحیح
        print("Response Content:")
        print(json.dumps(response.json(), indent=4, ensure_ascii=False))
    else:
        print("❌ خطایی در لاگین رخ داد.")
        print(f"Detail: {response.text}")

except requests.exceptions.ConnectionError:
    print("❌ خطا: سرور روشن نیست! ابتدا uvicorn را اجرا کن.")
