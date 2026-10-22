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
    assert 'class="fh-mod-trigger"' in html
    assert 'data-url="/dashboard"' in html
    assert '<span>Beasiswa</span>' in html


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


def test_wib_offset_expression_matches_utc_plus_7():
    """R14: strftime('%Y-%m','now','localtime') -> waktu WIB. Ekspresi offset tetap
    `now() at time zone interval '+07:00'` harus = UTC+7 (bukan UTC-7)."""
    from datetime import datetime, timedelta, timezone
    from database import get_conn
    conn = get_conn()
    got = conn.execute(
        "SELECT to_char(now() at time zone interval '+07:00', 'YYYY-MM-DD HH24')").fetchone()[0]
    conn.close()
    now_utc = datetime.now(timezone.utc)
    allowed = {(now_utc + timedelta(hours=7) + timedelta(minutes=d)).strftime("%Y-%m-%d %H") for d in (-1, 0, 1)}
    assert got in allowed


def test_etf_dashboard_paid_this_month_uses_wib_month():
    from datetime import datetime, timedelta, timezone
    from database import get_conn
    from modules.dashboard.service import get_etf_dashboard_data
    wib_month = (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m")
    conn = get_conn()
    conn.executemany(
        "INSERT INTO pam_records (company_id, pam_no, total_amount, status, tanggal_bayar) VALUES (2, ?, ?, ?, ?)",
        [("P-THIS", 1500, "complete", wib_month + "-01"),
         ("P-OLD", 999, "complete", "2001-01-01"),
         ("P-OPEN", 777, "open", wib_month + "-02")],
    )
    conn.close()
    assert get_etf_dashboard_data(2)["paid_this_month"] == 1500


def test_etf_dashboard_pa_actions_aggregates_students_and_total():
    """GROUP_CONCAT(DISTINCT s.nama) -> string_agg(DISTINCT ...); SUM jumlah_pembayaran per PA."""
    from database import get_conn
    from modules.dashboard.service import get_etf_dashboard_data
    conn = get_conn()
    s1 = conn.execute("INSERT INTO siswa (company_id, code, nama) VALUES (2, 'D1', 'Ani')").lastrowid
    s2 = conn.execute("INSERT INTO siswa (company_id, code, nama) VALUES (2, 'D2', 'Budi')").lastrowid
    pa = conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, created_at) VALUES (2, 'PA-D1', 'open', '2026-07-01')"
    ).lastrowid
    conn.executemany(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jumlah_pembayaran) VALUES (?, ?, ?)",
        [(pa, s1, 100), (pa, s1, 50), (pa, s2, 25)],
    )
    conn.close()
    data = get_etf_dashboard_data(2)
    item = next(it for it in data["pa_actions"] if it["pa_number"] == "PA-D1")
    assert sorted(item["nama_student"].split(",")) == ["Ani", "Budi"]
    assert item["total"] == 175
    assert data["pa_open"] == 1
