import io
import openpyxl
from modules.sponsorship.service import seed_perusahaan


def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_smt(client):
    client.post("/select-company", data={"company_id": "1"})


def _select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def _seed():
    seed_perusahaan([("SMART", "AGRI", "AGRI")])


def test_index_requires_login(client):
    resp = client.get("/sponsorship/")
    assert resp.status_code == 302


def test_index_renders_for_smt(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/")
    assert resp.status_code == 200
    assert b"Sponsorship" in resp.data
    assert b"Ganti Company" not in resp.data


def test_index_shows_wrong_company_notice_for_etf(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/")
    assert resp.status_code == 200
    assert b"Ganti Company" in resp.data


def test_api_dashboard_data_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/api/dashboard-data")
    assert resp.status_code == 403

def test_api_dashboard_data_accepts_multi_value_cat_and_pillar(client):
    login(client)
    _select_smt(client)
    _seed()
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
    })
    resp = client.get("/sponsorship/api/dashboard-data", query_string=[
        ("cat", "Sponsorship"), ("cat", "CSR Gedung"),
        ("cat3", "AGRI"), ("cat3", "APP"),
    ])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["summary"]["total_count"] == 1


def test_input_page_renders_for_smt(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/input")
    assert resp.status_code == 200
    assert b"Input" in resp.data


def test_input_page_has_cat1_search_and_lembaga_datalist(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/input")
    assert b'id="sp-in-cat1-search"' in resp.data
    assert b'id="sp-lembaga-datalist"' in resp.data


def test_api_lookups_returns_perusahaan_and_lembaga(client):
    login(client)
    _select_smt(client)
    _seed()
    resp = client.get("/sponsorship/api/lookups")
    data = resp.get_json()
    assert {"cat1": "SMART", "cat2": "AGRI", "cat3": "AGRI"} in data["perusahaan"]
    assert data["lembaga"] == []


def test_input_create_success(client):
    login(client)
    _select_smt(client)
    _seed()
    resp = client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
    })
    data = resp.get_json()
    assert data["ok"] is True


def test_input_create_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.post("/sponsorship/input/create", json={})
    assert resp.status_code == 403


def test_data_page_renders_with_seeded_transaksi(client):
    login(client)
    _select_smt(client)
    _seed()
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
    })
    resp = client.get("/sponsorship/data")
    assert resp.status_code == 200
    assert b"Yayasan Test" in resp.data


def test_data_get_and_update_single_record(client):
    login(client)
    _select_smt(client)
    _seed()
    created = client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
    }).get_json()
    tid = created["id"]
    resp = client.get(f"/sponsorship/data/{tid}")
    assert resp.get_json()["ok"] is True
    resp = client.post(f"/sponsorship/data/{tid}/update", json={"perihal": "Diperbarui"})
    assert resp.get_json()["ok"] is True


def test_report_page_renders_with_toolbar_and_buttons(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/report")
    assert resp.status_code == 200
    assert b"Sponsorship" in resp.data
    assert b"sp-report-cat4-btn" in resp.data


def test_dashboard_registered_in_nav_tabs():
    from modules.dashboard.routes import DASHBOARD_TABS
    keys = [t[2] for t in DASHBOARD_TABS]
    assert "sponsorship" in keys


def test_api_lookups_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/api/lookups")
    assert resp.status_code == 403


def test_data_get_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/data/1")
    assert resp.status_code == 403


def test_data_update_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.post("/sponsorship/data/1/update", json={"perihal": "x"})
    assert resp.status_code == 403


def test_data_page_pagination_preserves_filters(client):
    login(client)
    _select_smt(client)
    _seed()
    for _ in range(150):
        client.post("/sponsorship/input/create", json={
            "cat": "Sponsorship", "description": "Sosial",
            "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
            "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
        })
    resp = client.get("/sponsorship/data?cat3=AGRI&page=1")
    assert b"cat3=AGRI" in resp.data


def test_data_page_edit_modal_has_full_record_fields(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/data")
    assert b'id="sp-ed-cat"' in resp.data
    assert b'id="sp-ed-cat1-search"' in resp.data
    assert b'id="sp-ed-cat4"' in resp.data
    assert b'id="sp-ed-lembaga"' in resp.data
    assert b'id="sp-ed-tanggal-form"' in resp.data


def test_edit_modal_preserves_out_of_whitelist_description_on_unrelated_save(client):
    login(client)
    _select_smt(client)
    _seed()
    created = client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
    }).get_json()
    tid = created["id"]
    # Simulate a historical row with an out-of-whitelist description (as migration would produce)
    from database import get_conn
    conn = get_conn()
    conn.execute("UPDATE sponsorship_transaksi SET description = ? WHERE id = ?", ("Legacy Category Not In List", tid))
    conn.commit()
    conn.close()
    resp = client.post(f"/sponsorship/data/{tid}/update", json={"description": "Legacy Category Not In List", "perihal": "Edited"})
    assert resp.get_json()["ok"] is True


def test_api_report_data_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/api/report-data")
    assert resp.status_code == 403


def test_api_report_data_returns_expected_structure(client):
    login(client)
    _select_smt(client)
    _seed()
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
    })
    resp = client.get("/sponsorship/api/report-data?tahun=2026&cat4=all")
    data = resp.get_json()
    assert data["tahun"] == "2026"
    assert data["cat4_mode"] == "all"
    assert data["sections"][0]["description"] == "Sosial"
    assert data["grand_total"]["total"] == 1000


def test_api_report_data_defaults_cat4_to_all_when_invalid(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/api/report-data?cat4=bogus")
    data = resp.get_json()
    assert data["cat4_mode"] == "all"


def test_api_report_data_defaults_tahun_to_latest_available(client):
    login(client)
    _select_smt(client)
    _seed()
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2025-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Lama", "amount_request": 1000,
    })
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Baru", "amount_request": 2000,
    })
    resp = client.get("/sponsorship/api/report-data")  # no tahun param
    data = resp.get_json()
    assert data["tahun"] == "2026"


def test_export_report_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/report/export")
    assert resp.status_code == 403


def test_export_report_returns_xlsx_file(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/report/export?tahun=2026&cat4=all")
    assert resp.status_code == 200
    assert resp.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_report_page_has_toggle_buttons_and_table_container(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/report")
    assert resp.status_code == 200
    assert b'data-cat4="include"' in resp.data
    assert b'data-cat4="exclude"' in resp.data
    assert b'data-cat4="all"' in resp.data


def test_export_report_filename_matches_cat4_and_tahun(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/report/export?tahun=2026&cat4=include")
    assert "Sponsorship_Report_include_2026.xlsx" in resp.headers.get("Content-Disposition", "")


def test_report_page_tahun_dropdown_has_options_for_seeded_years(client):
    login(client)
    _select_smt(client)
    _seed()
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-15", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
    })
    resp = client.get("/sponsorship/report")
    assert b'<input type="checkbox" name="tahun" value="2026"' in resp.data
    assert b'id="sp-report-table-container"' in resp.data
    assert b'id="sp-report-tahun"' in resp.data
    assert b'id="sp-report-export"' in resp.data

def test_data_page_has_full_height_table_wrap_id(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/data")
    assert resp.status_code == 200
    assert b'id="sp-table-wrap"' in resp.data

def test_outstanding_page_has_full_height_table_wrap_id(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/outstanding")
    assert resp.status_code == 200
    assert b'id="sp-table-wrap"' in resp.data


def test_mr_page_renders_with_data(client):
    login(client)
    _select_smt(client)
    _seed()
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-20", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "perihal": "Bantuan Banjir",
        "amount_request": 1000,
    })
    resp = client.get("/sponsorship/mr?tahun=2026")
    assert resp.status_code == 200
    assert b"Yayasan Test" in resp.data
    assert b"A26-5-25-1" in resp.data


def test_mr_page_shows_wrong_company_notice_for_etf(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/mr")
    assert resp.status_code == 200
    assert b"Ganti Company" in resp.data


def test_mr_export_downloads_xlsx(client):
    login(client)
    _select_smt(client)
    _seed()
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-20", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
    })
    resp = client.get("/sponsorship/mr/export?tahun=2026")
    assert resp.status_code == 200
    assert resp.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_mr_export_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/mr/export")
    assert resp.status_code == 403


def test_mr_tab_in_toolbar(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/report")
    assert resp.status_code == 200
    assert b'href="/sponsorship/mr"' in resp.data


def test_vendor_page_requires_login(client):
    resp = client.get("/sponsorship/vendor")
    assert resp.status_code == 302


def test_vendor_page_renders_for_smt(client):
    login(client)
    _select_smt(client)
    _seed()
    resp = client.get("/sponsorship/vendor")
    assert resp.status_code == 200
    assert b"SMART" in resp.data


def test_vendor_page_shows_wrong_company_notice_for_etf(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/vendor")
    assert resp.status_code == 200
    assert b"Ganti Company" in resp.data


def test_vendor_create_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.post("/sponsorship/vendor/create", json={"cat1": "SMART", "cat2": "AGRI", "cat3": "AGRI"})
    assert resp.status_code == 403


def test_vendor_create_success(client):
    login(client)
    _select_smt(client)
    resp = client.post("/sponsorship/vendor/create", json={"cat1": "SMART", "cat2": "AGRI", "cat3": "AGRI"})
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_vendor_create_rejects_invalid_cat3(client):
    login(client)
    _select_smt(client)
    resp = client.post("/sponsorship/vendor/create", json={"cat1": "SMART", "cat2": "AGRI", "cat3": "NOT-A-PILLAR"})
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is False


def test_vendor_update_success(client):
    login(client)
    _select_smt(client)
    _seed()
    resp = client.post("/sponsorship/vendor/SMART/update", json={"cat2": "Mining", "cat3": "PROPERTY"})
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_vendor_update_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.post("/sponsorship/vendor/SMART/update", json={"cat2": "Mining", "cat3": "PROPERTY"})
    assert resp.status_code == 403


def test_vendor_delete_success(client):
    login(client)
    _select_smt(client)
    _seed()
    resp = client.post("/sponsorship/vendor/SMART/delete")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_vendor_delete_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.post("/sponsorship/vendor/SMART/delete")
    assert resp.status_code == 403


def _create(client, lem, tgl, cat4=None):
    payload = {"cat": "Sponsorship", "description": "Sosial", "tanggal_form_sponsor": tgl,
               "cat1": "SMART", "lembaga_perorangan": lem, "amount_request": 1000}
    if cat4:
        payload["cat4"] = cat4
    client.post("/sponsorship/input/create", json=payload)


def _seed_three_months(client):
    login(client)
    _select_smt(client)
    _seed()
    _create(client, "Jan Org", "2026-01-15", "Include")
    _create(client, "Feb Org", "2026-02-10", "Include")
    _create(client, "Mar Org", "2026-03-05", "Exclude")


def _lembaga(data):
    return sorted(r["lembaga_perorangan"] for s in data["sections"] for r in s["rows"])


def test_api_report_data_filters_by_bulan(client):
    _seed_three_months(client)
    data = client.get("/sponsorship/api/report-data?tahun=2026&cat4=all&bulan=01&bulan=02").get_json()
    assert _lembaga(data) == ["Feb Org", "Jan Org"]
    assert data["bulan"] == ["01", "02"] and data["bulan_label"] == "Jan, Feb"
    data = client.get("/sponsorship/api/report-data?tahun=2026&cat4=all&bulan=1").get_json()
    assert data["bulan"] == ["01"] and _lembaga(data) == ["Jan Org"]        # '1' means January


def test_api_report_data_ignores_invalid_bulan(client):
    _seed_three_months(client)
    data = client.get("/sponsorship/api/report-data?tahun=2026&cat4=all&bulan=13&bulan=abc&bulan=0&bulan=").get_json()
    assert data["bulan"] == [] and _lembaga(data) == ["Feb Org", "Jan Org", "Mar Org"]


def test_api_report_data_applies_bulan_in_every_tab_mode(client):
    _seed_three_months(client)
    get = lambda cat4: _lembaga(client.get(f"/sponsorship/api/report-data?tahun=2026&cat4={cat4}&bulan=01&bulan=03").get_json())
    assert get("include") == ["Jan Org"]
    assert get("exclude") == ["Mar Org"]
    assert get("all") == ["Jan Org", "Mar Org"]
    assert get("bib_include") == ["Jan Org"]


def test_export_report_follows_the_applied_filter_and_names_the_file(client):
    _seed_three_months(client)
    resp = client.get("/sponsorship/report/export?tahun=2026&cat4=include&bulan=01&bulan=02")
    assert resp.status_code == 200
    assert "Sponsorship_Report_include_2026_01-02.xlsx" in resp.headers.get("Content-Disposition", "")
    ws = openpyxl.load_workbook(io.BytesIO(resp.data)).active
    values = [c.value for row in ws.iter_rows() for c in row]
    assert "Jan Org" in values and "Feb Org" in values and "Mar Org" not in values
    assert "RANGKUMAN SPONSORSHIP 2026 - in Rp Full Amount" in values


def test_export_report_filename_has_no_month_part_without_bulan(client):
    _seed_three_months(client)
    resp = client.get("/sponsorship/report/export?tahun=2026&cat4=all")
    assert "Sponsorship_Report_all_2026.xlsx" in resp.headers.get("Content-Disposition", "")


def test_report_page_has_the_bulan_dropdown_and_terapkan_filter_label(client):
    login(client)
    _select_smt(client)
    html = client.get("/sponsorship/report").data.decode()
    assert 'id="sp-report-bulan-container"' in html and 'id="sp-report-bulan"' in html
    assert html.count('name="bulan"') == 12
    assert 'name="bulan" value="01"' in html and 'name="bulan" value="12"' in html
    assert "Januari" in html and "Desember" in html
    assert ">Terapkan Filter<" in html and ">Refresh<" not in html
    assert 'id="sp-report-refresh"' in html                      # id unchanged
    assert 'name="bulan" value="01" checked' not in html          # no month ticked by default


def test_report_js_exports_from_the_applied_filter_state(client):
    login(client)
    _select_smt(client)
    js = client.get("/static/js/sponsorship.js").data.decode()
    assert "bulan: []" in js and "_getReportBulan" in js and "_sponsorshipReportParams" in js
    export_handler = js.split('getElementById("sp-report-export")')[1][:900]
    assert "_sponsorshipReportParams()" in export_handler          # export uses the applied state
    assert 'params.append("tahun"' not in export_handler           # no hand-rolled query from raw ticks

def test_report_page_has_select_all_and_clear_all_for_tahun_and_bulan(client):
    login(client)
    _select_smt(client)
    html = client.get("/sponsorship/report").data.decode()
    for target in ("sp-report-tahun", "sp-report-bulan"):
        assert 'data-target="%s" data-checked="1">Pilih Semua<' % target in html
        assert 'data-target="%s" data-checked="0">Hapus Semua<' % target in html

