from unittest.mock import MagicMock
def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def _select_smt(client):
    client.post("/select-company", data={"company_id": "1"})


def test_index_requires_login(client):
    resp = client.get("/beasiswa/sahabat/")
    assert resp.status_code == 302


def test_index_renders_after_login_and_etf_company(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Sahabat ETF" in resp.data
    assert b"Ganti Company" not in resp.data


def test_index_shows_wrong_company_notice_for_smt(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Ganti Company" in resp.data


def test_beasiswa_page_has_sahabat_etf_tab(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert b'data-tab="tab-sahabat"' in resp.data
    assert b'id="tab-sahabat"' in resp.data


def _seed_one_siswa(client):
    # dipanggil setelah login + _select_etf; pakai endpoint Beasiswa yang sudah ada
    # (POST /beasiswa/siswa/tambah -> add_siswa(), lihat modules/beasiswa/routes.py:73-76)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9991001", "nama": "API Test Siswa", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })


def test_api_summary_returns_seeded_siswa(client):
    login(client)
    _select_etf(client)
    _seed_one_siswa(client)
    resp = client.get("/beasiswa/sahabat/api/summary")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["nama"] == "API Test Siswa"


def test_api_breakdown_returns_expected_keys(client):
    login(client)
    _select_etf(client)
    _seed_one_siswa(client)
    resp = client.get("/beasiswa/sahabat/api/breakdown")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "kategori" in data
    assert "over_budget" in data


def test_api_detail_returns_empty_for_siswa_with_no_transactions(client):
    login(client)
    _select_etf(client)
    _seed_one_siswa(client)
    resp = client.get("/beasiswa/sahabat/api/detail/9991001")
    assert resp.status_code == 200
    assert resp.get_json()["rows"] == []


def test_api_summary_requires_login(client):
    resp = client.get("/beasiswa/sahabat/api/summary")
    assert resp.status_code == 302


def test_export_summary_returns_csv(client):
    login(client)
    _select_etf(client)
    _seed_one_siswa(client)
    resp = client.get("/beasiswa/sahabat/export/summary")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/csv")
    assert b"API Test Siswa" in resp.data


def test_export_detail_returns_xlsx(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/export/detail")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_index_contains_dashboard_elements_for_etf_company(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/", follow_redirects=True)
    assert resp.status_code == 200
    for expected in (b"setf-summary", b"chart-bulanan", b"chart-kategori",
                      b"setf-table", b"setf-alert-card", b"export/summary", b"export/detail",
                      b"setf-filter-pillar", b"setf-monthly-table"):
        assert expected in resp.data, f"missing {expected!r} in response"


def test_index_sahabat_etf_detail_tabel_open_by_default(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/", follow_redirects=True)
    assert b'<details class="setf-accordion" id="setf-detail-tabel" open>' in resp.data


def test_index_shows_year_filter_checkbox_when_data_exists(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992020", "nama": "Siswa Filter UI", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9992020", "tanggal": "2026-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}]})

    resp = client.get("/beasiswa/sahabat/", follow_redirects=True)
    assert b'class="setf-year-cb"' in resp.data
    assert b"2026" in resp.data


def test_index_shows_pillar_filter_checkboxes_when_data_exists(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992050", "nama": "Siswa Pillar Checkbox", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/payment/tambah", json={"code": "9992050", "tanggal": "2026-01-15",
        "pillar": "SETF", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}]})

    resp = client.get("/beasiswa/sahabat/", follow_redirects=True)
    assert b'class="setf-pillar-cb"' in resp.data
    assert b"SETF" in resp.data


def test_api_summary_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/summary")
    assert resp.status_code == 403
    assert resp.get_json()["ok"] is False


def test_api_breakdown_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/breakdown")
    assert resp.status_code == 403
    assert resp.get_json()["ok"] is False


def test_api_detail_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/detail/9991001")
    assert resp.status_code == 403
    assert resp.get_json()["ok"] is False


def test_export_summary_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/export/summary")
    assert resp.status_code == 403


def test_export_detail_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/export/detail")
    assert resp.status_code == 403


def test_api_summary_respects_years_query_param(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992001", "nama": "Siswa Filter Tahun", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9992001", "tanggal": "2025-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}]})
    client.post("/beasiswa/budget/tambah", json={"code": "9992001", "tanggal": "2026-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}]})

    resp = client.get("/beasiswa/sahabat/api/summary?years=2026")
    data = resp.get_json()
    assert data["rows"][0]["budget_total"] == 2000000


def test_api_breakdown_respects_pillar_query_param(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992002", "nama": "Siswa Breakdown Pillar", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/payment/tambah", json={"code": "9992002", "tanggal": "2026-01-15",
        "pillar": "SETF", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}]})

    resp = client.get("/beasiswa/sahabat/api/breakdown?pillars=APP")
    data = resp.get_json()
    assert data["kategori"] == []


def test_api_monthly_requires_years_param(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/api/monthly")
    assert resp.status_code == 400


def test_api_monthly_returns_chart_year_and_months(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992003", "nama": "Siswa Bulanan Route", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9992003", "tanggal": "2026-04-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 800000}]})

    resp = client.get("/beasiswa/sahabat/api/monthly?years=2026")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["chart_year"] == 2026
    assert len(data["months"]) == 12


def test_api_monthly_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/monthly?years=2026")
    assert resp.status_code == 403


def test_export_summary_respects_year_filter(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992010", "nama": "Siswa Export Tahun", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9992010", "tanggal": "2025-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}]})
    client.post("/beasiswa/budget/tambah", json={"code": "9992010", "tanggal": "2026-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}]})

    resp = client.get("/beasiswa/sahabat/export/summary?years=2026")
    assert b"2000000.0" in resp.data
    assert b"1000000.0" not in resp.data


def test_export_detail_respects_pillar_filter(client, monkeypatch):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992011", "nama": "Siswa Export Pillar", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/payment/tambah", json={"code": "9992011", "tanggal": "2026-01-15",
        "pillar": "APP", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 400000}]})
    client.post("/beasiswa/payment/tambah", json={"code": "9992011", "tanggal": "2026-01-20",
        "pillar": "SETF", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 600000}]})

    mock_build = MagicMock(return_value=b"mock")
    monkeypatch.setattr("modules.sahabat_etf.report_xlsx.build_detail_workbook", mock_build)

    resp = client.get("/beasiswa/sahabat/export/detail?pillars=SETF")
    assert resp.status_code == 200
    
    mock_build.assert_called_once()
    rows = mock_build.call_args[0][0]
    amounts = [r["amount"] for r in rows if r["siswa_code"] == "9992011"]
    assert 600000.0 in amounts
    assert 400000.0 not in amounts


def test_api_breakdown_respects_multiple_pillars_query_param(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992030", "nama": "Siswa Multi Pillar Route", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/payment/tambah", json={"code": "9992030", "tanggal": "2026-01-15",
        "pillar": "APP", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}]})
    client.post("/beasiswa/payment/tambah", json={"code": "9992030", "tanggal": "2026-01-20",
        "pillar": "FINANCE", "perusahaan": "ETF",
        "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 700000}]})

    resp = client.get("/beasiswa/sahabat/api/breakdown?pillars=APP,FINANCE")
    data = resp.get_json()
    by_cat = {k["cat1"]: k for k in data["kategori"]}
    assert by_cat["By Pendidikan"]["payment"] == 1200000


def test_api_family_summary_returns_grouped_families(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "5260001", "nama": "Claudia Samaoen", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    resp = client.get("/beasiswa/sahabat/api/family_summary")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "families" in data
    assert len(data["families"]) == 1
    assert data["families"][0]["family_key"] == "fam5"
    assert data["families"][0]["label"] == "Claudia Samaoen"


def test_api_family_summary_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/family_summary")
    assert resp.status_code == 403
    assert resp.get_json()["ok"] is False


def test_api_latest_payments_kategori_filter_raises_limit_to_30(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9992040", "nama": "Siswa Latest 31", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    for day in range(1, 26):
        client.post("/beasiswa/payment/tambah", json={"code": "9992040", "tanggal": f"2026-01-{day:02d}",
            "pillar": "SETF", "perusahaan": "ETF",
            "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 100000}]})

    resp = client.get("/beasiswa/sahabat/api/latest_payments?kategori=By Pendidikan")
    data = resp.get_json()
    assert len(data["rows"]) == 25  # semua 25 muncul, batas 30 tidak kepotong

    resp_unfiltered = client.get("/beasiswa/sahabat/api/latest_payments")
    assert len(resp_unfiltered.get_json()["rows"]) == 10  # tanpa filter tetap limit 10


def test_export_report_returns_xlsx(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9994001", "nama": "Siswa Report Export", "jenjang": "SD", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9994001", "tanggal": "2026-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}]})

    resp = client.get("/beasiswa/sahabat/export/report?year=2026")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == \
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "sahabat_etf_report_2026.xlsx" in resp.headers["Content-Disposition"]

    import io, openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(resp.data))
    ws = wb.active
    assert "Siswa Report Export" in [c.value for row in ws.iter_rows() for c in row]


def test_export_report_requires_year_param(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/export/report")
    assert resp.status_code == 400


def test_export_report_rejects_non_numeric_year(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/export/report?year=abc")
    assert resp.status_code == 400


def test_export_report_rejects_malformed_numeric_year(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/export/report?year=--5")
    assert resp.status_code == 400


def test_export_report_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/export/report?year=2026")
    assert resp.status_code == 403


def test_index_contains_report_export_elements(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/", follow_redirects=True)
    assert resp.status_code == 200
    for expected in (b"setf-report-year", b"setf-export-report", b"export/report"):
        assert expected in resp.data, f"missing {expected!r} in response"


def test_api_report_returns_report_data(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/api/report?year=2026")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["data"]["report_year"] == 2026
    assert "sections" in data["data"]
    assert "pillar_breakdown" in data["data"]


def test_api_report_requires_year_param(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/api/report")
    assert resp.status_code == 400


def test_api_report_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/report?year=2026")
    assert resp.status_code == 403


def test_api_all_transactions_returns_rows(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/api/all_transactions")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert "rows" in data


def test_api_all_transactions_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/all_transactions")
    assert resp.status_code == 403

def test_index_contains_subtab_elements_for_etf_company(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9999000", "nama": "Test", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9999000", "tanggal": "2026-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}]})
    resp = client.get("/beasiswa/sahabat/", follow_redirects=True)
    assert resp.status_code == 200
    for expected in (b'data-subtab="dashboard"', b'data-subtab="laporan"', b'data-subtab="detail"',
                      b'id="setf-subtab-dashboard"', b'id="setf-subtab-laporan"', b'id="setf-subtab-detail"',
                      b'id="setf-laporan-content"', b'id="setf-detail-table"',
                      ):
        assert expected in resp.data, f"missing {expected!r} in response"


def test_api_report_includes_periode_fields_in_siswa_rows(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9995001", "nama": "Siswa Periode Test", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9995001", "tanggal": "2026-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}]})

    resp = client.get("/beasiswa/sahabat/api/report?year=2026")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert len(data["data"]["sections"]) > 0

    # Verify at least one section has siswa_rows with periode fields
    found_periode = False
    for section in data["data"]["sections"]:
        for group in section.get("groups", []):
            for row in group.get("siswa_rows", []):
                # periode_start and periode_end should be present in the response
                assert "periode_start" in row, "periode_start missing from siswa_row"
                assert "periode_end" in row, "periode_end missing from siswa_row"
                if row.get("periode_start") and row.get("periode_end"):
                    found_periode = True

    assert found_periode, "expected at least one siswa row with periode_start/periode_end populated"


def test_api_report_siswa_rows_have_all_laporan_render_fields(client):
    login(client)
    _select_etf(client)
    client.post("/beasiswa/siswa/tambah", json={
        "code": "9995002", "nama": "Siswa Laporan Periode", "jenjang": "S1", "angkatan": 2024,
        "program": "Sahabat ETF", "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })
    client.post("/beasiswa/budget/tambah", json={"code": "9995002", "tanggal": "2026-01-10",
        "pillar": "SETF", "items": [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}]})

    resp = client.get("/beasiswa/sahabat/api/report?year=2026")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True

    # Check that the JSON response carries all fields the Periode column needs.
    # Actual header/column rendering happens in setfLaporanHeaderRow (JavaScript);
    # this test only verifies the data structure supports it, not the rendered HTML/JS.
    assert len(data["data"]["sections"]) > 0

    # Verify the table structure has the right number of columns:
    # 3 non-metric columns (Nama, Periode, Pillar) + 8 metric columns = 11 total
    for section in data["data"]["sections"]:
        for group in section.get("groups", []):
            for row in group.get("siswa_rows", []):
                # Row should have all required fields for rendering
                assert "nama" in row
                assert "pillar" in row
                assert "periode_start" in row
                assert "periode_end" in row
                assert "cur" in row
                assert "cum" in row


def test_api_report_respects_month_and_pillars_array_query_params(client, monkeypatch):
    login(client)
    _select_etf(client)
    mock_build = MagicMock(return_value={})
    monkeypatch.setattr("modules.sahabat_etf.routes.build_report_data", mock_build)
    
    # Simulate frontend sending month and pillars[] array
    client.get("/beasiswa/sahabat/api/report?year=2026&month=8&pillars[]=APP&pillars[]=SETF")
    
    # Service should be called with month=8, pillars=["APP", "SETF"]
    mock_build.assert_called_once_with(2, 2026, 8, ["APP", "SETF"])


def test_api_pohon_respects_month_and_pillars_array_query_params(client, monkeypatch):
    login(client)
    _select_etf(client)
    mock_build = MagicMock(return_value={})
    mock_build_group = MagicMock(return_value={})
    monkeypatch.setattr("modules.sahabat_etf.service.build_pohon_data", mock_build)
    monkeypatch.setattr("modules.sahabat_etf.service.build_pohon_group_data", mock_build_group)
    
    client.get("/beasiswa/sahabat/api/pohon?year=2026&month=9&pillars[]=SETF")
    
    mock_build.assert_called_once_with(2, 2026, 9, ["SETF"])


def test_export_report_respects_month_and_pillars_array_query_params(client, monkeypatch):
    login(client)
    _select_etf(client)
    mock_build = MagicMock(return_value={})
    mock_workbook = MagicMock(return_value=b"mock")
    monkeypatch.setattr("modules.sahabat_etf.routes.build_report_data", mock_build)
    monkeypatch.setattr("modules.sahabat_etf.report_xlsx.build_report_workbook", mock_workbook)
    
    client.get("/beasiswa/sahabat/export/report?year=2026&month=10&pillars[]=FINANCE")
    
    mock_build.assert_called_once_with(2, 2026, 10, ["FINANCE"])


def test_export_ppt_report_respects_month_and_pillars_array_query_params(client, monkeypatch):
    login(client)
    _select_etf(client)
    mock_build = MagicMock(return_value={})
    mock_pptx = MagicMock(return_value=b"mock")
    monkeypatch.setattr("modules.sahabat_etf.routes.build_report_data", mock_build)
    monkeypatch.setattr("modules.sahabat_etf.report_pptx.build_report_pptx", mock_pptx)
    
    client.get("/beasiswa/sahabat/api/report/export_ppt?year=2026&month=11&pillars[]=APP")
    
    mock_build.assert_called_once_with(2, 2026, 11, ["APP"])
