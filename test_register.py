import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1/auth"
PHONE = "09123456789"

print("--- Step 1: Sending OTP Request ---")
try:
    otp_response = requests.post(
        f"{BASE_URL}/otp/send",
        headers={"Content-Type": "application/json"},
        json={"phone": PHONE}
    )

    # چاپ پاسخ با انکودینگ درست پایتون
    otp_data = otp_response.json()
    print(json.dumps(otp_data, indent=4, ensure_ascii=False))

    otp_code = otp_data.get("code_debug_only")

    if not otp_code:
        print("❌ Error: 'code_debug_only' not found in response!")
        exit()

    print(f"\n🔑 Code received: {otp_code}")
    print("\n--- Step 2: Registering User ---")

    register_response = requests.post(
        f"{BASE_URL}/register",
        params={"otp_code": otp_code},
        headers={"Content-Type": "application/json"},
        json={
            "name": "صادق",
            "phone": PHONE,
            "password": "SecurePassword123",
            "role": "patient"
        }
    )

    register_data = register_response.json()
    print(json.dumps(register_data, indent=4, ensure_ascii=False))

except Exception as e:
    print(f"An error occurred: {e}")
