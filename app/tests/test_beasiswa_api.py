import pytest
from app import create_app


def _login(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    data = r.get_json()
    return data.get("access_token", "")


def test_get_siswa_requires_auth(client):
    r = client.get("/api/v1/siswa?company=ETF")
    assert r.status_code == 401


def test_get_siswa_empty(client):
    token = _login(client)
    r = client.get("/api/v1/siswa?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert isinstance(body["data"], list)


def test_get_rekap(client):
    token = _login(client)
    r = client.get("/api/v1/rekap?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_invalid_company(client):
    token = _login(client)
    r = client.get("/api/v1/siswa?company=INVALID",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_get_payment_beasiswa(client):
    token = _login(client)
    r = client.get("/api/v1/payment?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_get_budget_requires_siswa_code(client):
    token = _login(client)
    r = client.get("/api/v1/budget?company=ETF",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
