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
    resp = client.get("/beasiswa/sahabat/")
    assert resp.status_code == 200
    assert b"Sahabat ETF" in resp.data
    assert b"Ganti Company" not in resp.data


def test_index_shows_wrong_company_notice_for_smt(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/")
    assert resp.status_code == 200
    assert b"Ganti Company" in resp.data


def test_beasiswa_page_has_link_to_sahabat_etf(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert b"/beasiswa/sahabat" in resp.data


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


def test_export_detail_returns_csv(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/export/detail")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/csv")
    assert b"Sumber" in resp.data  # header row


def test_index_contains_dashboard_elements_for_etf_company(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/")
    assert resp.status_code == 200
    for expected in (b"setf-summary", b"chart-bulanan", b"chart-kategori",
                      b"setf-table", b"setf-alert-card", b"export/summary", b"export/detail",
                      b"setf-filter-pillar", b"setf-monthly-table"):
        assert expected in resp.data, f"missing {expected!r} in response"


def test_index_sahabat_etf_detail_tabel_open_by_default(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/")
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

    resp = client.get("/beasiswa/sahabat/")
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

    resp = client.get("/beasiswa/sahabat/")
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


def test_export_detail_respects_pillar_filter(client):
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

    resp = client.get("/beasiswa/sahabat/export/detail?pillars=SETF")
    assert b"600000.0" in resp.data
    assert b"400000.0" not in resp.data


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
