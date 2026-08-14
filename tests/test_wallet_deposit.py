# tests/test_wallet_deposit.py

from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models.wallet import Wallet


class MockPaymentGateway:
    """درگاه جعلی برای تست Integration بدون اتصال به بانک"""

    def create_payment(self, amount, order_id, callback_url, **kwargs):
        mock_res = MagicMock()
        mock_res.authority = "FAKE-AUTH-123"
        mock_res.payment_url = "https://fake-bank.ir/pay"
        return mock_res

    def verify_payment(self, authority, **kwargs):
        return True


# ─── پیکربندی مسیر API ────────────────────────────────────────
API_PREFIX = "/api/v1"
WALLET_BASE = f"{API_PREFIX}/wallet"


def test_deposit_flow_integration(
    client,
    db_session,
    test_user,
    patient_token_headers,
):
    """
    چرخه کامل شارژ کیف پول:
    1. POST /api/v1/wallet/deposit ← ایجاد تراکنش و دریافت authority
    2. GET /api/v1/wallet/verify ← تایید بانک و افزایش موجودی
    3. بررسی دیتابیس
    """
    patch_path = "app.api.routes.wallet.get_payment_gateway"

    with patch(patch_path, return_value=MockPaymentGateway()):

        # ─── گام ۱: درخواست شارژ ───────────────────────────────
        response = client.post(
            f"{WALLET_BASE}/deposit",
            json={"amount": 2000, "description": "شارژ آزمایشی"},
            headers=patient_token_headers,
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert data["authority"] == "FAKE-AUTH-123"

        # ─── گام ۲: کال‌بک بانک ────────────────────────────────
        verify_response = client.get(
            f"{WALLET_BASE}/verify?authority=FAKE-AUTH-123&Status=OK",
            headers=patient_token_headers,
        )

        assert verify_response.status_code == 200, verify_response.text
        result = verify_response.json()
        assert result["success"] is True

        # ─── گام ۳: تأیید دیتابیس ──────────────────────────────
        db_session.expire_all()
        wallet = (
            db_session.query(Wallet)
            .filter(Wallet.user_id == test_user.id)
            .first()
        )

        assert wallet is not None, "کیف پول یافت نشد"
        assert wallet.balance == Decimal("2000.00"), (
            f"موجودی اشتباه: {wallet.balance}"
        )


def test_deposit_flow_failure(
    client,
    db_session,
    test_user,
    patient_token_headers,
):
    """
    سناریوی ناموفق: بانک Status=NOK برمی‌گرداند.
    موجودی کیف پول نباید افزایش یابد.
    """
    patch_path = "app.api.routes.wallet.get_payment_gateway"

    with patch(patch_path, return_value=MockPaymentGateway()):

        # ─── ایجاد تراکنش ──────────────────────────────────────
        deposit_response = client.post(
            f"{WALLET_BASE}/deposit",
            json={"amount": 1000, "description": "شارژ ناموفق"},
            headers=patient_token_headers,
        )

        assert deposit_response.status_code == 200, deposit_response.text

        # ─── کال‌بک ناموفق ─────────────────────────────────────
        verify_response = client.get(
            f"{WALLET_BASE}/verify?authority=FAKE-AUTH-123&Status=NOK",
            headers=patient_token_headers,
        )

        assert verify_response.status_code == 200, verify_response.text
        result = verify_response.json()
        assert result["success"] is False

        # ─── موجودی نباید تغییر کند ────────────────────────────
        db_session.expire_all()
        wallet = (
            db_session.query(Wallet)
            .filter(Wallet.user_id == test_user.id)
            .first()
        )

        assert wallet is not None
        assert wallet.balance == Decimal("0.00"), (
            f"موجودی نباید افزایش یابد: {wallet.balance}"
        )
