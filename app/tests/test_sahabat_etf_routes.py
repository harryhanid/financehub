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
    for expected in (b"setf-summary", b"chart-siswa", b"chart-kategori",
                      b"setf-table", b"setf-alert-card", b"export/summary", b"export/detail"):
        assert expected in resp.data, f"missing {expected!r} in response"
