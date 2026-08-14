# test_wallet.py
import json
import os
import sys
from uuid import uuid4

import requests

BASE = "http://127.0.0.1:8000/api/v1"

# Windows console را برای نمایش فارسی امن کن
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    # 1) Login — توکن از متغیر محیطی یا مقدار پیش‌فرض
    phone = os.getenv("TEST_DOCTOR_PHONE", "09120000000")
    password = os.getenv("TEST_DOCTOR_PASSWORD", "doctor123")

    r = requests.post(
        f"{BASE}/auth/login",
        json={"phone": phone, "password": password},
        timeout=15,
    )

    if not r.ok:
        raise RuntimeError(f"Doctor login failed: status={r.status_code}, response={r.text}")

    headers = {"Authorization": f"Bearer {r.json()['token']['access_token']}"}

    # 2) Top-up — reference_id یکتا تا تداخلی نباشد
    r = requests.post(
        f"{BASE}/doctor-wallet/topup",
        json={
            "amount": 1000,
            "reference_id": f"PYTEST-{uuid4().hex[:8]}",
            "description": "پرداخت آزمایشی",
        },
        headers=headers,
        timeout=15,
    )
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
