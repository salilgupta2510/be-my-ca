import pytest

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

USER = {
    "email": "test@example.com",
    "password": "Password123!",
    "full_name": "Test User",
    "role": "layman",
}


async def test_register_returns_token(client):
    r = await client.post(REGISTER_URL, json=USER)
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["role"] == "layman"
    assert data["onboarding_complete"] is False


async def test_register_duplicate_email(client):
    await client.post(REGISTER_URL, json=USER)
    r = await client.post(REGISTER_URL, json=USER)
    assert r.status_code == 400
    assert "already registered" in r.json()["detail"].lower()


async def test_login_valid_credentials(client):
    await client.post(REGISTER_URL, json=USER)
    r = await client.post(LOGIN_URL, json={"email": USER["email"], "password": USER["password"]})
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_login_wrong_password(client):
    await client.post(REGISTER_URL, json=USER)
    r = await client.post(LOGIN_URL, json={"email": USER["email"], "password": "wrongpassword"})
    assert r.status_code == 401


async def test_login_unknown_email(client):
    r = await client.post(LOGIN_URL, json={"email": "nobody@example.com", "password": "anything"})
    assert r.status_code == 401
