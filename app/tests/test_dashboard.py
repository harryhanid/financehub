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

def test_navbar_shows_module_menu_on_dashboard(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    html = resp.data.decode()
    assert 'class="navbar-menu-item active" href="/dashboard"' in html
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


def test_navbar_module_menu_appears_on_other_pages_too(client):
    login(client)
    select_etf(client)
    resp = client.get("/bank/")
    html = resp.data.decode()
    assert 'class="navbar-menu-item active" href="/bank/"' in html
    assert 'href="/dashboard"' in html
    assert "Beasiswa" in html
