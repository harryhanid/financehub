# app/tests/test_payment_memo_open_pam.py


def _login(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})
    return r


def _select_company(client):
    client.post("/select-company", data={"company_id": "2"})


def test_open_pam_page_exposes_drafts_json(client):
    """Open PAM tab must contain OPEN_PAM_DRAFTS JS constant for client-side grouping."""
    _login(client)
    _select_company(client)
    resp = client.get("/payment-memo/")
    assert resp.status_code == 200
    assert b"OPEN_PAM_DRAFTS" in resp.data


def test_open_pam_has_energy_tab(client):
    _login(client)
    _select_company(client)
    resp = client.get("/payment-memo/")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'tab=energy' in html or 'tab_btn energy' in html or 'tab=energy' in html or "energy" in html
    assert "EFIN" in html or "EFIN" in html
