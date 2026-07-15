import random

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def make_user_payload():
    rand = random.randint(100000, 999999)
    return {
        "name": f"Test User {rand}",
        "phone": f"09{random.randint(100000000, 999999999)}",
        "email": f"test{rand}@example.com",
        "password": "Test123456!",
    }


def test_register_login_me_flow():
    payload = make_user_payload()

    register_response = client.post("/api/v1/auth/register", json=payload)
    assert register_response.status_code in (200, 201), register_response.text

    login_response = client.post(
        "/api/v1/auth/login",
        json={"phone": payload["phone"], "password": payload["password"]},
    )
    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["phone"] == payload["phone"]


def test_register_duplicate_phone_fails():
    payload = make_user_payload()

    first_response = client.post("/api/v1/auth/register", json=payload)
    assert first_response.status_code in (200, 201), first_response.text

    second_payload = payload.copy()
    second_payload["email"] = f"other_{payload['email']}"

    second_response = client.post("/api/v1/auth/register", json=second_payload)
    assert second_response.status_code == 400, second_response.text


def test_register_duplicate_email_fails():
    payload = make_user_payload()

    first_response = client.post("/api/v1/auth/register", json=payload)
    assert first_response.status_code in (200, 201), first_response.text

    second_payload = payload.copy()
    second_payload["phone"] = f"09{random.randint(100000000, 999999999)}"

    second_response = client.post("/api/v1/auth/register", json=second_payload)
    assert second_response.status_code == 400, second_response.text


def test_login_with_wrong_password_fails():
    payload = make_user_payload()

    register_response = client.post("/api/v1/auth/register", json=payload)
    assert register_response.status_code in (200, 201), register_response.text

    login_response = client.post(
        "/api/v1/auth/login",
        json={"phone": payload["phone"], "password": "WrongPassword123!"},
    )
    assert login_response.status_code in (400, 401), login_response.text


def test_me_without_token_fails():
    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code in (401, 403), me_response.text
