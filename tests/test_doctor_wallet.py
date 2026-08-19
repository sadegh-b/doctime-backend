from decimal import Decimal
from uuid import uuid4


BASE_URL = "/api/v1/doctor-wallet"


def to_decimal(value) -> Decimal:
    """
    Convert API monetary values safely to Decimal.
    """
    return Decimal(str(value))


def test_get_balance_authenticated(client, doctor_token_headers):
    response = client.get(
        BASE_URL,
        headers=doctor_token_headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "balance" in data
    assert to_decimal(data["balance"]) >= Decimal("0")


def test_get_balance_unauthorized(client):
    response = client.get(BASE_URL)

    assert response.status_code == 401, response.text


def test_get_balance_as_patient(client, patient_token_headers):
    response = client.get(
        BASE_URL,
        headers=patient_token_headers,
    )

    assert response.status_code == 403, response.text


def test_topup_wallet_success(client, doctor_token_headers):
    amount = Decimal("50000")
    unique_reference_id = f"TEST_REF_{uuid4().hex}"

    balance_response = client.get(
        BASE_URL,
        headers=doctor_token_headers,
    )

    assert balance_response.status_code == 200, balance_response.text

    balance_before = to_decimal(
        balance_response.json()["balance"]
    )

    payload = {
        "amount": int(amount),
        "reference_id": unique_reference_id,
        "description": "Test wallet topup",
    }

    response = client.post(
        f"{BASE_URL}/topup",
        json=payload,
        headers=doctor_token_headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["message"] == "کیف پول با موفقیت شارژ شد"
    assert "wallet" in data
    assert "balance" in data["wallet"]

    balance_after = to_decimal(
        data["wallet"]["balance"]
    )

    assert balance_after == balance_before + amount
