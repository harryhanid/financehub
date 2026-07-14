# tests/test_dashboard.py

def login(client):
    return client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})

def select_etf(client):
    client.post("/select-company", data={"company_id": "2"})

def test_dashboard_redirect_without_login(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]

def test_select_company_page_requires_login(client):
    resp = client.get("/select-company")
    assert resp.status_code == 302

def test_select_company_after_login(client):
    login(client)
    resp = client.get("/select-company")
    assert resp.status_code == 200
    assert b"Pilih" in resp.data

def test_dashboard_after_company_selection(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data

def test_dashboard_shows_etf_stats(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    assert b"Total Siswa" in resp.data

def test_dashboard_shows_module_tabs(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    html = resp.data.decode()
    assert 'class="tab-btn active" href="/dashboard"' in html
    for label, href in [
        ("Beasiswa", "/beasiswa/"),
        ("Payment Approval Memo", "/payment-memo/"),
        ("Payment Application", "/etf-payment-application/"),
        ("Budget", "/budget/"),
        ("Bank", "/bank/"),
        ("Users", "/users/"),
    ]:
        assert f'href="{href}"' in html
        assert label in html
    assert "Account Payable" not in html
    assert "Coming Soon" not in html
