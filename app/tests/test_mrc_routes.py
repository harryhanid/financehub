import io
import re

from modules.general_ledger import service as gl_service
from modules.management_report import coa_map
from modules.management_report import routes as mr_routes
from tests.test_gl_sync import mkrow
from tests.test_mrc_sources import LOG, insert_sponsor

COMBINE_HEADERS = ["Account Management", "ID#", "Date", "Allocation Memo", "Budget Activity", "COST CENTER",
                   "DEBIT - CREDIT", "Source", "COA HO", "COST CENTER2", "Month", "CC0", "CC1", "BC1",
                   "New Code", "Memo", "BC"]
APPEND1_HEADERS = ["COA", "MM", "YY", "CC", "CC.1", "Category", "Activity", "Description", "PTA", "Custom",
                   "MM.1", "ACT", "BGT"]
CMAP_ROWS = [
    {"source": "SMT", "account": "6-1810", "coa_ho": "70108100", "category": "10 - Office Supplies", "code": "-10-"},
    {"source": "ETF", "account": "6-2190", "coa_ho": "70119100", "category": "20 - Others", "code": "-20-"}]
CC_ROWS = [
    {"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": "SMT - IT"},
    {"cost_center": "POCFAD", "total_cc": "$POCFOF", "seq": 9, "description": "SMT - Finance"},
    {"cost_center": "TFOPEX", "total_cc": "$TFOPEX", "seq": 6, "description": "ETF - Opex"},
    {"cost_center": "POSPON", "total_cc": "$POCCOM", "seq": 5, "description": "SMT - Sponshorship"}]


def login(client, user="admin", password="Admin@123"):
    client.post("/auth/login", json={"username": user, "password": password})
    client.post("/select-company", data={"company_id": "2"})


def seed(client_sponsor=True, mapping=True):
    gl_service.replace_year("smt", 2026, [
        mkrow(acc_management="6-1810", tgl="2026-01-15", debit_credit=-957910.0, job_name="POITEC",
              budget_activity="SMT - IT", allocation_memo="Zoom", id_no="GJ-00168"),
        mkrow(acc_management="6-1810", tgl="2026-02-10", debit_credit=5000000.0, job_name="POCFAD",
              budget_activity="SMT - Finance", allocation_memo="ATK", id_no="GJ-00200")], LOG)
    gl_service.replace_year("etf", 2026, [
        mkrow(acc_management="6-2190", tgl="2026-02-05", debit_credit=30000.0, job_name="TFOPEX",
              budget_activity="", allocation_memo="Biaya admin", id_no="BK2-0126")], LOG)
    if client_sponsor:
        from modules.management_report import combine_sources
        insert_sponsor(combine_sources.smt_company_id(), "2026-01-19", "Prasasti Membership", 500000000.0)
    if mapping:
        coa_map.sync_coa("m.xlsb", "u", CMAP_ROWS, CC_ROWS)


def headers(html):
    return [re.sub(r"<.*?>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", html, re.S)]


def test_pages_require_login(client):
    for url in ("/management-report/gl-combine", "/management-report/append1"):
        resp = client.get(url)
        assert resp.status_code == 302 and "/auth/login" in resp.headers["Location"]


def test_gl_combine_page_shows_the_17_headers_and_all_three_sources(client):
    login(client)
    seed()
    html = client.get("/management-report/gl-combine").data.decode()
    assert headers(html) == COMBINE_HEADERS
    for text in ("Zoom", "ATK", "Biaya admin", "Prasasti Membership", "Sponsor", "$POCCOM", "A26-51"):
        assert text in html, text
    assert "-957.910" in html                                    # DEBIT - CREDIT in full rupiah
    assert "19/01/2026" in html                                  # dd/mm/yyyy


def test_append1_page_shows_the_13_headers_and_workbook_values(client):
    login(client)
    seed()
    html = client.get("/management-report/append1").data.decode()
    assert headers(html) == APPEND1_HEADERS
    assert "701078002" in html and "POSPON" in html and "500,0" in html
    assert "- Act 2026 : Prasasti Membership Month : 1" in html


def test_new_code_numbering_ignores_source_cutoff_and_search(client):
    login(client)
    seed()
    from modules.management_report import combine_sources
    insert_sponsor(combine_sources.smt_company_id(), "2026-02-12", "Februari Sponsor", 100000000.0)
    for qs in ("?source=Sponsor&q=Februari", "?source=Sponsor&q=Februari&mm=2", "?q=Februari"):
        html = client.get("/management-report/gl-combine" + qs).data.decode()
        assert "A26-52" in html and "A26-51" not in html, qs
    jan = client.get("/management-report/gl-combine?source=Sponsor&mm=1").data.decode()
    assert "A26-51" in jan and "A26-52" not in jan and "Februari Sponsor" not in jan


def test_navbar_shows_user_and_company_on_the_new_pages(client):
    login(client)
    seed()
    idx = client.get("/management-report/").data.decode()
    company = re.search(r'class="navbar-company"[^>]*>(.*?)</a>', idx, re.S).group(1).strip()
    assert company
    for url in ("/management-report/gl-combine", "/management-report/append1"):
        html = client.get(url).data.decode()
        assert re.search(r'class="navbar-company"[^>]*>\s*' + re.escape(company), html), url
        user = re.search(r'class="navbar-user">.*?</svg>\s*(\S+)', html, re.S).group(1)
        assert user == "admin", (url, user)


def test_source_filter_and_invalid_source(client):
    login(client)
    seed()
    sp = client.get("/management-report/gl-combine?source=Sponsor").data.decode()
    assert "Prasasti Membership" in sp and "Zoom" not in sp and "Biaya admin" not in sp
    etf = client.get("/management-report/gl-combine?source=ETF").data.decode()
    assert "Biaya admin" in etf and "Zoom" not in etf and "Prasasti" not in etf
    bad = client.get("/management-report/gl-combine?source=NOPE")
    assert bad.status_code == 200 and "Zoom" in bad.data.decode() and "Prasasti" in bad.data.decode()


def test_cumulative_cutoff_defaults_to_latest_month(client):
    login(client)
    seed()
    jan = client.get("/management-report/gl-combine?yy=2026&mm=1").data.decode()
    assert "Zoom" in jan and "Prasasti" in jan and "ATK" not in jan and "Biaya admin" not in jan
    latest = client.get("/management-report/gl-combine").data.decode()
    assert "ATK" in latest and "Zoom" in latest                 # cumulative through the latest month


def test_invalid_parameters_fall_back_without_error(client):
    login(client)
    seed()
    for qs in ("?yy=abc&mm=99", "?yy=1999", "?mm=0", "?page=abc", "?page=-5", "?cc=NOPE", "?source=%3Cscript%3E"):
        for url in ("/management-report/gl-combine", "/management-report/append1"):
            assert client.get(url + qs).status_code == 200, (url, qs)


def test_user_input_is_html_escaped(client):
    login(client)
    seed()
    html = client.get("/management-report/gl-combine?q=%3Cscript%3Ealert(1)%3C/script%3E&cc=%3Cscript%3E").data.decode()
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_empty_states(client):
    login(client)
    seed(mapping=False)
    assert "Pemetaan COA belum ada" in client.get("/management-report/gl-combine").data.decode()


def test_no_source_data_message(client):
    login(client)
    coa_map.sync_coa("m.xlsb", "u", CMAP_ROWS, CC_ROWS)
    assert "Belum ada data sumber" in client.get("/management-report/gl-combine").data.decode()


def test_old_style_mapping_shows_one_resync_banner(client):
    login(client)
    seed(mapping=False)
    coa_map.sync_coa("m.xlsb", "u", CMAP_ROWS)                  # coa rows only, no cc rows
    html = client.get("/management-report/gl-combine").data.decode()
    assert html.count("Pemetaan perlu disync ulang") == 1 and "belum ada di sheet CC" not in html


def test_unmapped_account_and_cost_center_banners(client):
    login(client)
    seed()
    gl_service.replace_year("smt", 2026, [
        mkrow(acc_management="6-9999", tgl="2026-02-20", debit_credit=2000000.0, job_name="POXXXX",
              allocation_memo="Misterius")], LOG)
    html = client.get("/management-report/gl-combine").data.decode()
    assert "Belum dipetakan" in html and "6-9999" in html and "POXXXX" in html and "belum ada di sheet CC" in html


def test_tab_bar_links_and_old_tabs_unchanged(client):
    login(client)
    seed()
    page = client.get("/management-report/gl-combine").data.decode()
    for href in ("/management-report/gl-combine", "/management-report/append1", "/management-report/?tab=sync"):
        assert href in page, href
    index = client.get("/management-report/").data.decode()
    assert 'data-tab="tab-sync"' in index and 'data-tab="tab-report"' in index and 'data-tab="tab-ho"' in index
    links = re.findall(r'<a [^>]*href="/management-report/(?:gl-combine|append1|pemetaan)"[^>]*>', index)
    assert len(links) == 3 and all("mr-linktab" in l and "tab-btn" not in l for l in links)
    for url in ("/management-report/gl-combine", "/management-report/append1"):
        html = client.get(url).data.decode()
        pem = re.findall(r'<a [^>]*href="/management-report/pemetaan"[^>]*>', html)
        assert len(pem) == 2                                     # tab link + "Kelola pemetaan" link
        assert any("mr-linktab" in l and "tab-btn" not in l for l in pem)


def test_combine_pages_have_slim_mapping_line_and_no_sync_controls(client):
    login(client)
    seed()
    for url in ("/management-report/gl-combine", "/management-report/append1"):
        html = client.get(url).data.decode()
        assert "mr-map-btn" not in html and "mr-map-file" not in html and "mrSyncMapping" not in html
        assert "Kelola pemetaan" in html and "SMT 1 akun, ETF 1 akun, 4 cost center" in html
        assert "Pemetaan: terakhir sync" in html


def test_combine_page_without_any_sync_says_never_synced(client):
    login(client)
    seed(mapping=False)
    html = client.get("/management-report/gl-combine").data.decode()
    assert "Pemetaan belum pernah disync" in html and "Kelola pemetaan" in html


def upload(client, name="Master.xlsb"):
    return client.post("/management-report/gl-combine/sync-mapping", data={"file": (io.BytesIO(b"x"), name)},
                       content_type="multipart/form-data")


def test_sync_mapping_success_unchanged_and_bad_uploads(client, monkeypatch):
    login(client)
    monkeypatch.setattr(mr_routes.coa_map, "read_mapping_sheets", lambda f: (CMAP_ROWS, CC_ROWS))
    j = upload(client).get_json()
    assert j["ok"] and j["changed"] and "SMT 1 akun" in j["pesan"] and "4 cost center" in j["pesan"]
    again = upload(client).get_json()
    assert again["ok"] and again["changed"] is False and "Sudah sinkron" in again["pesan"]
    assert upload(client, "a.xlsx").status_code == 400
    assert client.post("/management-report/gl-combine/sync-mapping", data={},
                       content_type="multipart/form-data").status_code == 400

    def boom(f):
        raise coa_map.CoaParseError("Sheet 'CC' tidak ditemukan di file.")
    monkeypatch.setattr(mr_routes.coa_map, "read_mapping_sheets", boom)
    r = upload(client)
    assert r.status_code == 400 and "tidak ditemukan" in r.get_json()["pesan"]
    assert len(coa_map.get_map()) == 2


def test_sync_mapping_database_error_is_json_500(client, monkeypatch):
    login(client)
    monkeypatch.setattr(mr_routes.coa_map, "read_mapping_sheets", lambda f: (CMAP_ROWS, CC_ROWS))

    def boom(*a, **k):
        raise RuntimeError("database is locked")
    monkeypatch.setattr(mr_routes.coa_map, "sync_coa", boom)
    r = upload(client)
    assert r.status_code == 500 and r.get_json()["ok"] is False and "database is locked" in r.get_json()["pesan"]


def test_non_admin_can_view_but_not_sync(client):
    import bcrypt
    import database
    pw_hash = bcrypt.hashpw(b"Req@12345", bcrypt.gensalt(4)).decode()
    conn = database.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role, must_change_pw) VALUES (?, ?, 'requester', 0)",
                 ("req1", pw_hash))
    conn.commit()
    conn.close()
    assert client.post("/auth/login", json={"username": "req1", "password": "Req@12345"}).status_code == 200
    client.post("/select-company", data={"company_id": "2"})
    seed()
    assert upload(client).status_code == 403


def test_mc_filters():
    assert mr_routes._mc_num(-957910.0) == "-957.910" and mr_routes._mc_num(None) == ""
    assert mr_routes._mc_mio(1234.56) == "1.234,6" and mr_routes._mc_mio(-1e-17) == "0,0"
    assert mr_routes._mc_date("2026-01-15") == "15/01/2026" and mr_routes._mc_date("") == ""


# ---------- R25: a database outage reaches the app's 503 handler ----------

def _outage(*a, **k):
    from fhdb.errors import OperationalError
    raise OperationalError("database unreachable")


def test_sync_mapping_database_outage_is_503(client, monkeypatch):
    login(client)
    monkeypatch.setattr(mr_routes.coa_map, "read_mapping_sheets", lambda f: (CMAP_ROWS, CC_ROWS))
    monkeypatch.setattr(mr_routes.coa_map, "sync_coa", _outage)
    assert upload(client).status_code == 503


def test_category_sync_database_outage_is_503(client, monkeypatch):
    login(client)
    monkeypatch.setattr(mr_routes.category_map, "read_category_sheet",
                        lambda f: [{"source": "SMT", "account": "6-1"}])
    monkeypatch.setattr(mr_routes.category_map, "sync_categories", _outage)
    r = client.post("/management-report/pemetaan/kategori/sync",
                    data={"file": (io.BytesIO(b"x"), "GL - MASTER.xlsb")}, content_type="multipart/form-data")
    assert r.status_code == 503


def test_mapping_page_database_outage_is_503_not_panel_error(client, monkeypatch):
    seed()
    login(client)
    monkeypatch.setattr(mr_routes.combine_sources, "gl_rows", _outage)
    assert client.get("/management-report/pemetaan").status_code == 503
