# tests/test_gl_routes.py
import io

from modules.general_ledger import routes as gl_routes
from modules.general_ledger import service as svc
from modules.general_ledger.parser import ParseError, ParseResult
from tests.test_gl_sync import mkrow


def login(client, user="admin", password="Admin@123"):
    client.post("/auth/login", json={"username": user, "password": password})
    client.post("/select-company", data={"company_id": "2"})


def _sync(client, monkeypatch, rows, dropped=0, entity="smt", name="Master.xlsb", year=2026):
    monkeypatch.setattr(gl_routes, "read_gl_sheet", lambda f, sheet: ParseResult(rows, dropped))
    data = {"file": (io.BytesIO(b"x"), name)}
    if year is not None:
        data["year"] = str(year)
    return client.post(f"/general-ledger/{entity}/sync", data=data,
                       content_type="multipart/form-data")


def test_pages_require_login(client):
    for url in ("/general-ledger/", "/general-ledger/smt"):
        resp = client.get(url)
        assert resp.status_code == 302 and "/auth/login" in resp.headers["Location"]


def test_index_redirects_to_smt(client):
    login(client)
    resp = client.get("/general-ledger/")
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/general-ledger/smt")


def test_unknown_entity_is_404(client):
    login(client)
    assert client.get("/general-ledger/xyz").status_code == 404


def test_three_tabs_render_and_empty_state(client):
    login(client)
    html = client.get("/general-ledger/etf").data.decode()
    assert "GL SMT" in html and "GL ETF" in html and "GL SETF" in html
    assert "Belum ada data" in html


def test_sync_success_then_unchanged(client, monkeypatch):
    login(client)
    rows = [mkrow(id_no="GJ-1", debit=10.0), mkrow(id_no="GJ-2", debit=0.0, credit=10.0)]
    r = _sync(client, monkeypatch, rows, dropped=3)
    j = r.get_json()
    assert r.status_code == 200 and j["ok"] and j["changed"] and "2 baris" in j["pesan"]
    assert "3" in j["pesan"]                                   # dropped rows reported
    again = _sync(client, monkeypatch, rows).get_json()
    assert again["ok"] and again["changed"] is False and "Sudah sinkron" in again["pesan"]


def test_sync_warns_when_unbalanced(client, monkeypatch):
    login(client)
    j = _sync(client, monkeypatch, [mkrow(debit=10.0, credit=0.0)]).get_json()
    assert j["ok"] and "tidak balance" in j["pesan"].lower()


def test_synced_data_is_listed_and_filtered(client, monkeypatch):
    login(client)
    _sync(client, monkeypatch, [mkrow(id_no="GJ-1", memo="Zoom langganan"),
                                mkrow(id_no="BK-9", memo="Listrik")])
    html = client.get("/general-ledger/smt").data.decode()
    assert "Zoom langganan" in html and "Listrik" in html
    html = client.get("/general-ledger/smt?q=Listrik").data.decode()
    assert "Listrik" in html and "Zoom langganan" not in html
    assert "Zoom langganan" not in client.get("/general-ledger/etf").data.decode()


def test_bad_page_param_does_not_error(client, monkeypatch):
    login(client)
    _sync(client, monkeypatch, [mkrow()])
    for qs in ("page=999", "page=abc", "page=-3"):
        assert client.get("/general-ledger/smt?" + qs).status_code == 200


def test_sync_rejects_non_xlsb(client):
    login(client)
    r = client.post("/general-ledger/smt/sync",
                    data={"file": (io.BytesIO(b"x"), "a.xlsx"), "year": "2026"},
                    content_type="multipart/form-data")
    assert r.status_code == 400 and "xlsb" in r.get_json()["pesan"]


def test_sync_without_file_is_400(client):
    login(client)
    r = client.post("/general-ledger/smt/sync", data={}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_parse_error_keeps_old_data(client, monkeypatch):
    login(client)
    _sync(client, monkeypatch, [mkrow(memo="keep me")])

    def boom(f, sheet):
        raise ParseError("Sheet 'GL SMT' tidak ditemukan di file.")
    monkeypatch.setattr(gl_routes, "read_gl_sheet", boom)
    r = client.post("/general-ledger/smt/sync", data={"file": (io.BytesIO(b"x"), "m.xlsb"), "year": "2026"},
                    content_type="multipart/form-data")
    assert r.status_code == 400 and "tidak ditemukan" in r.get_json()["pesan"]
    assert svc.query_rows("smt", {})["total"] == 1


def test_sync_with_no_valid_rows_is_400(client, monkeypatch):
    login(client)
    r = _sync(client, monkeypatch, [], dropped=5)
    assert r.status_code == 400


def test_sync_unknown_entity_is_404(client):
    login(client)
    r = client.post("/general-ledger/xyz/sync", data={"file": (io.BytesIO(b"x"), "m.xlsb"), "year": "2026"},
                    content_type="multipart/form-data")
    assert r.status_code == 404


def test_database_error_during_sync_returns_json_500(client, monkeypatch):
    login(client)

    def boom(*a, **k):
        raise RuntimeError("database is locked")
    monkeypatch.setattr(gl_routes.gl_sync, "sync_rows", boom)
    r = _sync(client, monkeypatch, [mkrow()])
    assert r.status_code == 500 and r.get_json()["ok"] is False
    assert "database is locked" in r.get_json()["pesan"]


def test_non_admin_can_view_but_not_sync(client, monkeypatch):
    import bcrypt
    import database
    pw_hash = bcrypt.hashpw(b"Req@12345", bcrypt.gensalt(4)).decode()
    conn = database.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role, must_change_pw) "
                 "VALUES (?, ?, 'requester', 0)", ("req1", pw_hash))
    conn.commit()
    conn.close()
    assert client.post("/auth/login", json={"username": "req1", "password": "Req@12345"}).status_code == 200
    client.post("/select-company", data={"company_id": "2"})
    assert client.get("/general-ledger/smt").status_code == 200
    assert b"gl-sync-btn" not in client.get("/general-ledger/smt").data
    r = _sync(client, monkeypatch, [mkrow()])
    assert r.status_code == 403
    assert svc.query_rows("smt", {})["total"] == 0


def test_page_shows_every_imported_column(client, monkeypatch):
    login(client)
    _sync(client, monkeypatch, [mkrow(sub_category="Zoom Sub", ket20="K20 value", pph_non_pph="PPH23",
                                      category_lk="LK cat", accrual_actual="Accrual")])
    html = client.get("/general-ledger/smt").data.decode()
    for label in ("PPH/Non PPH", "Keterangan 20", "DEBIT - CREDIT", "Sub-Category", "Accrual/Actual"):
        assert label in html, label
    for value in ("Zoom Sub", "K20 value", "PPH23", "LK cat", "Accrual"):
        assert value in html, value


def test_old_mr_tab_is_gone_from_the_general_ledger_module(client):
    login(client)
    for url in ("/general-ledger/mr", "/general-ledger/mr/sync-coa"):
        assert client.get(url).status_code in (404, 405)
    html = client.get("/general-ledger/smt").data.decode()
    assert "/general-ledger/mr" not in html
    for label in ("GL SMT", "GL ETF", "GL SETF"):
        assert label in html


# ---------- multi-year ----------

def test_sync_requires_a_valid_year(client, monkeypatch):
    login(client)
    for bad in (None, "", "abc", "1999", "2101"):
        r = _sync(client, monkeypatch, [mkrow()], year=bad)
        assert r.status_code == 400 and "tahun" in r.get_json()["pesan"].lower(), bad
    assert svc.query_rows("smt", {})["total"] == 0


def test_sync_skips_rows_outside_the_chosen_year_and_reports_them(client, monkeypatch):
    login(client)
    rows = [mkrow(id_no="A", tgl="2025-12-31"), mkrow(id_no="B", tgl="2026-01-02"),
            mkrow(id_no="C", tgl=None)]
    j = _sync(client, monkeypatch, rows, year=2026).get_json()
    assert j["ok"] and j["rows"] == 1 and j["skipped_year"] == 2
    assert "2 baris di luar 2026" in j["pesan"]
    assert [r["id_no"] for r in svc.query_rows("smt", {})["rows"]] == ["B"]


def test_sync_with_no_row_in_the_chosen_year_is_400_and_changes_nothing(client, monkeypatch):
    login(client)
    _sync(client, monkeypatch, [mkrow(id_no="keep", tgl="2026-01-02")], year=2026)
    r = _sync(client, monkeypatch, [mkrow(id_no="x", tgl="2026-05-05")], year=2025)
    assert r.status_code == 400 and "2025" in r.get_json()["pesan"]
    assert [x["id_no"] for x in svc.query_rows("smt", {})["rows"]] == ["keep"]


def test_syncing_another_year_does_not_touch_existing_years(client, monkeypatch):
    login(client)
    _sync(client, monkeypatch, [mkrow(id_no="N26", tgl="2026-01-02")], year=2026)
    j = _sync(client, monkeypatch, [mkrow(id_no="N25", tgl="2025-03-03")], year=2025).get_json()
    assert j["ok"] and j["changed"]
    assert svc.years_with_data("smt") == [2026, 2025]
    assert svc.query_rows("smt", {"year": 2026})["total"] == 1
    assert svc.query_rows("smt", {"year": 2025})["total"] == 1


def test_viewer_defaults_to_latest_year_and_year_filter_switches(client, monkeypatch):
    login(client)
    _sync(client, monkeypatch, [mkrow(memo="memo dua-enam", tgl="2026-01-02")], year=2026)
    _sync(client, monkeypatch, [mkrow(memo="memo dua-lima", tgl="2025-03-03")], year=2025)
    html = client.get("/general-ledger/smt").data.decode()
    assert "memo dua-enam" in html and "memo dua-lima" not in html
    html = client.get("/general-ledger/smt?year=2025").data.decode()
    assert "memo dua-lima" in html and "memo dua-enam" not in html
    assert 'name="year"' in html


def test_sync_form_has_a_year_selector_for_admin(client):
    login(client)
    html = client.get("/general-ledger/smt").data.decode()
    assert 'id="gl-sync-year"' in html


def test_report_tolerates_non_iso_dates(client):
    # Review Focus 4: non-ISO / empty tgl must not break the year-grouped GL page (substr(tgl,1,4) per year).
    from database import get_conn
    conn = get_conn()
    try:
        for tgl in ("15/03/2025", "", "2025-03-01"):
            conn.execute('INSERT INTO "GLSMT" (entry_no, id_no, tgl, debit, credit) VALUES (?,?,?,?,?)',
                         (1, f"GJ-{tgl}", tgl, 1.0, 0.0))
    finally:
        conn.close()
    login(client)
    resp = client.get("/general-ledger/smt?year=2025")
    assert resp.status_code == 200
    assert svc.years_with_data("smt") == [2025]             # '15/0' and '' are not years
    assert svc.query_rows("smt", {"year": 2025})["total"] == 1
