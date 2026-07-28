# Path: test_me_auth.py
import requests
import json

# ۱. ابتدا باید توکن را از مرحله قبل داشته باشی (من اینجا توکنی که گرفتی را می‌گذارم)
# نکته: در دنیای واقعی، فرانت‌اِند این توکن را در LocalStorage ذخیره می‌کند
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODU1ODM4NjAsInN1YiI6IjQifQ.HN1voHG8LfxdPMthtlbyUFlFHAwsKywJvj5ozPuSoSs"

url = "http://127.0.0.1:8000/api/v1/auth/me"

# ۲. ارسال توکن در هدر درخواست (Standard Bearer Token)
headers = {
    "Authorization": f"Bearer {TOKEN}"
}

print("--- در حال استعلام اطلاعات کاربری با توکن ---")

try:
    response = requests.get(url, headers=headers)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        print("✅ احراز هویت با موفقیت تایید شد.")
        print(json.dumps(response.json(), indent=4, ensure_ascii=False))
    elif response.status_code == 401:
        print("❌ خطای عدم دسترسی: توکن معتبر نیست یا منقضی شده است.")
    else:
        print(f"❌ خطای غیرمنتظره: {response.text}")

except Exception as e:
    print(f"❌ خطا در اتصال: {e}")
