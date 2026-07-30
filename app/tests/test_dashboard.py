import json
# tests/test_dashboard.py

def login(client):
    return client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})

def select_etf(client):
    client.post("/select-company", data={"company_id": "2"})

def select_smt(client):
    client.post("/select-company", data={"company_id": "1"})

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


def test_navbar_hides_sponsorship_for_etf(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    html = resp.data.decode()
    assert "Beasiswa" in html
    assert "Sponsorship" not in html


def test_navbar_hides_beasiswa_for_smt(client):
    login(client)
    select_smt(client)
    resp = client.get("/dashboard")
    html = resp.data.decode()
    assert "Sponsorship" in html
    assert "Beasiswa" not in html


def test_dashboard_page_opts_into_view_transitions(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    html = resp.data.decode()
    assert "@view-transition" in html
    assert "view-transition-name: flow-wordmark" in html


def _nav_modules(html):
    marker = '<script type="application/json" id="fh-nav-modules-data">'
    start = html.index(marker) + len(marker)
    end = html.index("</script>", start)
    return json.loads(html[start:end])


def test_nav_modules_subtabs_for_etf(client):
    login(client)
    select_etf(client)
    resp = client.get("/dashboard")
    by_key = {m["key"]: m for m in _nav_modules(resp.data.decode())}
    assert "sponsorship" not in by_key
    assert [t["tab"] for t in by_key["beasiswa"]["subtabs"]] == [
        "dashboard", "siswa", "budget", "payment", "laporan", "rekam", "sahabat"
    ]
    assert [t["tab"] for t in by_key["payment_memo"]["subtabs"]] == [
        "draft-pay", "input-payment", "pam", "fiori", "sml", "setf", "pa-advance", "vendors", "draft-memo"
    ]
    assert by_key["dashboard"]["subtabs"] == []
    assert by_key["users"]["subtabs"] == []


def test_nav_modules_subtabs_for_smt(client):
    login(client)
    select_smt(client)
    resp = client.get("/dashboard")
    by_key = {m["key"]: m for m in _nav_modules(resp.data.decode())}
    assert "beasiswa" not in by_key
    assert [t["tab"] for t in by_key["payment_memo"]["subtabs"]] == [
        "draft-pay", "input-payment", "smt", "advance", "draft-memo"
    ]
    assert [t["url"] for t in by_key["sponsorship"]["subtabs"]] == [
        "/sponsorship/", "/sponsorship/input", "/sponsorship/data", "/sponsorship/report"
    ]
    assert [t["url"] for t in by_key["budget"]["subtabs"]] == [
        "/budget/master", "/budget/realisasi", "/budget/carryover"
    ]
