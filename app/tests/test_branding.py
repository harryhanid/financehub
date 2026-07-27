# tests/test_branding.py

def login(client):
    return client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})


def select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def test_dashboard_navbar_shows_flow_not_finance_hub(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    html = resp.data.decode()
    assert "FLOW" in html
    assert "Finance Hub" not in html


def test_dashboard_page_title_is_flow(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    html = resp.data.decode()
    assert "<title>Dashboard — FLOW</title>" in html


def test_base_html_links_favicon(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    html = resp.data.decode()
    assert 'rel="icon"' in html
    assert "favicon.svg" in html


def test_login_page_shows_flow_branding(client):
    resp = client.get("/auth/login")
    html = resp.data.decode()
    assert "<title>Login — FLOW</title>" in html
    assert "Finance Hub" not in html
    assert "Financial Ledger and Operational Workspace" in html
    assert 'rel="icon"' in html


def test_login_page_wordmark_uses_flow_text(client):
    resp = client.get("/auth/login")
    html = resp.data.decode()
    assert '<span class="wordmark-text">FLOW</span>' in html


def test_company_select_page_shows_flow_branding(client):
    login(client)
    resp = client.get("/select-company")
    html = resp.data.decode()
    assert "<title>Pilih Perusahaan — FLOW</title>" in html
    assert "FINANCE HUB" not in html
    assert 'rel="icon"' in html
    assert '<span class="wordmark-text">FLOW</span>' in html


def test_company_select_page_has_a_panel_per_company(client):
    login(client)
    resp = client.get("/select-company")
    html = resp.data.decode()
    assert 'class="company-panel company-panel-smt"' in html
    assert 'class="company-panel company-panel-etf"' in html
    assert 'name="company_id" value="1"' in html
    assert 'name="company_id" value="2"' in html
    assert "Sinar Mas Tjipta" in html
    assert "Eka Tjipta Foundation" in html


def test_change_password_page_shows_flow_title(client):
    login(client)
    resp = client.get("/auth/change-password")
    html = resp.data.decode()
    assert "<title>Ganti Password — FLOW</title>" in html
    assert 'rel="icon"' in html
