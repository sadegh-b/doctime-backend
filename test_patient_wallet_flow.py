# test_patient_wallet_flow.py
"""
Manual integration test for the patient wallet payment flow.

Run:
    python test_patient_wallet_flow.py

Required:
    - FastAPI server running on http://127.0.0.1:8000
    - Test user exists with the configured phone and password
"""

import sys
from decimal import Decimal

import requests


BASE = "http://127.0.0.1:8000/api/v1"

# اطلاعات کاربر تست؛ در صورت نیاز فقط این دو مقدار را تغییر بده.
PHONE = "09123456789"
PASSWORD = "Test@1234"

DEPOSIT_AMOUNT = Decimal("1000")
TIMEOUT_SECONDS = 15


# Windows console را برای نمایش فارسی امن می‌کند.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def print_response_error(response: requests.Response) -> None:
    """نمایش خوانای پاسخ خطا از API."""
    print(f"\nHTTP {response.status_code}")
    try:
        print("Response body:", response.json())
    except ValueError:
        print("Response body:", response.text)


def assert_equal(actual, expected, message: str) -> None:
    """Assertion ساده با پیام دقیق برای اجرای اسکریپت مستقل."""
    if actual != expected:
        raise AssertionError(
            f"{message}\nExpected: {expected!r}\nActual:   {actual!r}"
        )


def request_or_raise(method: str, url: str, **kwargs) -> requests.Response:
    """ارسال request با timeout و نمایش body در صورت خطا."""
    response = requests.request(
        method=method,
        url=url,
        timeout=TIMEOUT_SECONDS,
        **kwargs,
    )

    if not response.ok:
        print_response_error(response)
        response.raise_for_status()

    return response


def login() -> dict:
    """ورود و ساخت header احراز هویت."""
    response = request_or_raise(
        "POST",
        f"{BASE}/auth/login",
        json={
            "phone": PHONE,
            "password": PASSWORD,
        },
    )

    data = response.json()
    access_token = data["token"]["access_token"]

    if not access_token:
        raise AssertionError("Login response does not contain access_token.")

    print("@1 Login: OK")
    return {"Authorization": f"Bearer {access_token}"}


def get_wallet(headers: dict) -> dict:
    """دریافت موجودی فعلی کیف پول."""
    response = request_or_raise("GET", f"{BASE}/wallet/me", headers=headers)

    wallet = response.json()

    required_fields = {"wallet_id", "user_id", "balance"}
    missing_fields = required_fields - wallet.keys()
    if missing_fields:
        raise AssertionError(
            f"Wallet response misses fields: {sorted(missing_fields)}"
        )

    print(
        "@2 Wallet before deposit: OK | "
        f"wallet_id={wallet['wallet_id']} | balance={wallet['balance']}"
    )
    return wallet


def create_deposit(headers: dict) -> dict:
    """ایجاد تراکنش pending برای شارژ کیف پول."""
    response = request_or_raise(
        "POST",
        f"{BASE}/wallet/deposit",
        headers=headers,
        json={
            "amount": str(DEPOSIT_AMOUNT),
            "description": "تست یکپارچه شارژ کیف پول",
        },
    )

    deposit = response.json()

    assert_equal(deposit["success"], True, "Deposit request must be successful.")

    if not deposit.get("authority"):
        raise AssertionError("Deposit response does not contain authority.")

    print(
        "@3 Deposit: OK | "
        f"authority={deposit['authority']} | "
        f"payment_url={deposit.get('payment_url')}"
    )
    return deposit


def verify_deposit(authority: str) -> dict:
    """
    تایید موفق پرداخت.

    نکته: طبق قرارداد فعلی API، Status باید با S بزرگ ارسال شود.
    """
    response = request_or_raise(
        "GET",
        f"{BASE}/wallet/verify",
        params={"authority": authority, "Status": "OK"},
    )

    verification = response.json()

    assert_equal(verification["success"], True, "Payment verification must be successful.")

    print(
        "@4 Verify: OK | "
        f"tracking_code={verification['tracking_code']} | "
        f"amount={verification['amount']}"
    )
    return verification


def verify_again_must_be_idempotent(authority: str) -> dict:
    """
    اجرای مجدد verify روی authority یکسان.

    این تست فقط بررسی می‌کند درخواست fail نمی‌شود؛
    مقدار اصلی موجودی قبل/بعد نیز در main بررسی خواهد شد.
    """
    response = request_or_raise(
        "GET",
        f"{BASE}/wallet/verify",
        params={"authority": authority, "Status": "OK"},
    )

    result = response.json()

    print(
        "@5 Re-verify: OK | "
        f"success={result['success']} | "
        f"message={result['message']}"
    )
    return result


def main() -> None:
    print("=" * 60)
    print("PATIENT WALLET INTEGRATION TEST")
    print("=" * 60)

    headers = login()

    wallet_before = get_wallet(headers)
    balance_before = Decimal(str(wallet_before["balance"]))

    deposit = create_deposit(headers)
    authority = deposit["authority"]

    verify_deposit(authority)

    wallet_after_first_verify = get_wallet(headers)
    balance_after_first_verify = Decimal(str(wallet_after_first_verify["balance"]))

    expected_balance = balance_before + DEPOSIT_AMOUNT
    assert_equal(
        balance_after_first_verify,
        expected_balance,
        "Balance after successful verification is incorrect.",
    )

    print(
        "@6 Balance increment: OK | "
        f"{balance_before} + {DEPOSIT_AMOUNT} = {balance_after_first_verify}"
    )

    # تست مهم مالی: verify تکراری نباید موجودی را دوباره افزایش دهد.
    verify_again_must_be_idempotent(authority)

    wallet_after_second_verify = get_wallet(headers)
    balance_after_second_verify = Decimal(str(wallet_after_second_verify["balance"]))

    assert_equal(
        balance_after_second_verify,
        balance_after_first_verify,
        "Idempotency failed: duplicate verify changed the wallet balance.",
    )

    print(
        "@7 Idempotency: OK | "
        f"balance remains {balance_after_second_verify}"
    )

    response = request_or_raise(
        "GET",
        f"{BASE}/wallet/transactions",
        headers=headers,
    )
    transactions = response.json()

    if not isinstance(transactions, list):
        raise AssertionError("Transactions response must be a list.")

    matching_transaction = next(
        (
            transaction
            for transaction in transactions
            if transaction.get("tracking_code") == authority
        ),
        None,
    )

    if matching_transaction is None:
        raise AssertionError("Verified transaction was not found in wallet history.")

    print(
        "@8 Transactions history: OK | "
        f"transaction_id={matching_transaction['id']} | "
        f"status={matching_transaction['status']}"
    )

    print("\n" + "=" * 60)
    print("ALL WALLET TESTS PASSED ✅")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        print(f"\nREQUEST FAILED ❌\n{exc}")
        raise SystemExit(1) from exc
    except (AssertionError, KeyError, ValueError) as exc:
        print(f"\nTEST FAILED ❌\n{exc}")
        raise SystemExit(1) from exc
