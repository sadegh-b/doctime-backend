import requests
import json

url = "http://127.0.0.1:8000/api/v1/auth/login"
payload = {
    "phone": "09999999999",
    "password": "SecurePassword123"
}

response = requests.post(url, json=payload)

print(f"Status Code: {response.status_code}")
# اینجا با جادوی ensure_ascii=False متن فارسی را درست می‌بینیم
print("Response JSON:")
print(json.dumps(response.json(), indent=4, ensure_ascii=False))
