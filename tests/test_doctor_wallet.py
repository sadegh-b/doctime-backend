def test_get_balance_authenticated(client, doctor_token_headers):

    response = client.get(
        "/api/v1/doctor-wallet/balance",
        headers=doctor_token_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "balance" in data


def test_get_balance_unauthorized(client):

    response = client.get(
        "/api/v1/doctor-wallet/balance"
    )

    assert response.status_code == 401


def test_get_balance_as_patient(client, patient_token_headers):

    response = client.get(
        "/api/v1/doctor-wallet/balance",
        headers=patient_token_headers
    )

    assert response.status_code == 403


def test_topup_wallet_success(client, doctor_token_headers):

    payload = {
        "amount": 50000,
        "reference_id": "TEST_REF_001",
        "description": "Test wallet topup"
    }

    response = client.post(
        "/api/v1/doctor-wallet/topup",
        json=payload,
        headers=doctor_token_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Wallet topped up successfully"

    assert data["wallet"]["balance"] >= 50000
