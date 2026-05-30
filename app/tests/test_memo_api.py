import pytest
from app import create_app


def _login(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    return r.get_json().get("access_token", "")


def test_get_draft_payments_empty(client):
    token = _login(client)
    r = client.get("/api/v1/payment-draft?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    assert r.get_json()["data"] == []


def test_list_memo_empty(client):
    token = _login(client)
    r = client.get("/api/v1/payment-memo?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.get_json()["data"], list)


def test_create_memo_requires_verificator(client):
    # admin is 'releaser' — only verificator can create memo
    token = _login(client)
    r = client.post("/api/v1/payment-memo",
                    json={"company": "ETF", "tanggal": "2026-05-30", "notes": "", "item_ids": []},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_payment_draft_invalid_company(client):
    token = _login(client)
    r = client.get("/api/v1/payment-draft?company=INVALID",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_list_memo_invalid_company(client):
    token = _login(client)
    r = client.get("/api/v1/payment-memo?company=XYZ",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_payment_draft_requires_auth(client):
    r = client.get("/api/v1/payment-draft?company=ETF")
    assert r.status_code == 401
