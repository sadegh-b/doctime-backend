# test_wallet.py
import json
import sys
from uuid import uuid4

import requests

BASE = "http://127.0.0.1:8000/api/v1"

# Windows console را برای نمایش فارسی امن کن
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def main():
    # 1) Login — توکن تازه در همین فرآیند
    r = requests.post(f"{BASE}/auth/login",
                      json={"phone": "09120000000", "password": "doctor123"})
    r.raise_for_status()
    headers = {"Authorization": f"Bearer {r.json()['token']['access_token']}"}

    # 2) Top-up — reference_id یکتا تا تداخلی نباشد
    r = requests.post(f"{BASE}/doctor-wallet/topup",
                      json={
                          "amount": 1000,
                          "reference_id": f"PYTEST-{uuid4().hex[:8]}",
                          "description": "پرداخت آزمایشی",
                      },
                      headers=headers)
    r.raise_for_status()
    data = r.json()

    # 3) نمایش + ذخیره UTF-8
    print("description =>", data["transaction"]["description"])
    print("id         =>", data["transaction"]["id"])
    print("balance    =>", data["wallet"]["balance"])

    with open("wallet_test_result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("\nsaved -> wallet_test_result.json (open it in VS Code)")

if __name__ == "__main__":
    main()
