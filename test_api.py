# test_api.py
import json
import sys
from uuid import uuid4

import requests

BASE = "http://127.0.0.1:8000/api/v1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def check(label, cond):
    status = "OK  " if cond else "FAIL"
    print(f"[{status}] {label}")
    return cond

def main():
    results = []

    # 1) Login
    r = requests.post(f"{BASE}/auth/login",
                      json={"phone": "09120000000", "password": "doctor123"})
    results.append(check("login", r.status_code == 200))
    token = r.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2) Balance
    r = requests.get(f"{BASE}/doctor-wallet/balance", headers=headers)
    bal = r.json().get("balance")
    results.append(check(f"balance (={bal})", r.status_code == 200 and bal is not None))

    # 3) Top-up
    r = requests.post(f"{BASE}/doctor-wallet/topup", headers=headers,
                      json={"amount": 500, "reference_id": f"AUTO-{uuid4().hex[:8]}",
                            "description": "تست خودکار"})
    results.append(check(f"topup ({r.status_code})", r.status_code == 201))

    # 4) Transactions
    r = requests.get(f"{BASE}/doctor-wallet/transactions", headers=headers)
    tx = r.json()
    results.append(check(f"transactions count={len(tx)}", r.status_code == 200 and len(tx) > 0))

    # 5) Unauthorized guard
    r = requests.get(f"{BASE}/doctor-wallet/balance")
    results.append(check("reject no-token (401)", r.status_code == 401))

    with open("test_api_result.json", "w", encoding="utf-8") as f:
        json.dump({"all_ok": all(results), "results": len(results)}, f, ensure_ascii=False, indent=2)

    print(f"\nTOTAL: {sum(results)}/{len(results)} passed")

if __name__ == "__main__":
    main()
