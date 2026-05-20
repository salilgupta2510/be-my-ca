"""All protected routes must return 401 without a valid token."""
import pytest

PROTECTED = [
    ("GET",  "/api/v1/gst/gstr2b?period=012025"),
    ("POST", "/api/v1/gst/reconciliation/run?period=012025"),
    ("GET",  "/api/v1/gst/reconciliation/results?period=012025"),
    ("GET",  "/api/v1/gst/reconciliation/summary?period=012025"),
    ("POST", "/api/v1/business"),
    ("GET",  "/api/v1/invoices/inward"),
    ("GET",  "/api/v1/invoices/outward"),
    ("GET",  "/api/v1/returns/gstr1"),
    ("GET",  "/api/v1/compliance/due-dates"),
]


@pytest.mark.parametrize("method,path", PROTECTED)
async def test_no_token_returns_401(client, method, path):
    r = await client.request(method, path)
    assert r.status_code == 401


async def test_invalid_token_returns_401(client):
    headers = {"Authorization": "Bearer not.a.real.token"}
    r = await client.get("/api/v1/gst/gstr2b?period=012025", headers=headers)
    assert r.status_code == 401


async def _get_token(client) -> str:
    r = await client.post("/api/v1/auth/register", json={
        "email": "auth@example.com",
        "password": "Password123!",
        "full_name": "Auth User",
        "role": "layman",
    })
    return r.json()["access_token"]


async def test_valid_token_passes_auth(client):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    # GSTR-2B with valid token should not be 401 (may be 200 with empty list)
    r = await client.get("/api/v1/gst/gstr2b?period=012025", headers=headers)
    assert r.status_code != 401
