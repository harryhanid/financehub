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


# ── PAM API tests ────────────────────────────────────────────────────────────

def test_get_coa_list(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get("/payment-memo/coa",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert len(data["coa"]) == 14


def test_get_pam_list_empty(client):
    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.get("/payment-memo/pam",
                    headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True
    assert data["rows"] == []


def test_update_pam_gl_account_via_api(client):
    from modules.payment_memo.service import create_pam_record
    from database import get_conn
    # Seed a PAM record directly
    conn = get_conn()
    pam_no = create_pam_record(conn, 2, "ETF", {
        "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
        "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
    })
    conn.commit()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]
    conn.close()

    token = _login(client)
    with client.session_transaction() as sess:
        sess["company_id"] = 2
    rv = client.post(f"/payment-memo/pam/{pam_id}/gl-account",
                     json={"gl_account": "70107800"},
                     headers={"Authorization": f"Bearer {token}"})
    assert rv.status_code == 200
    assert rv.get_json()["ok"] is True
