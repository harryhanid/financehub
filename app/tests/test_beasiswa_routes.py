def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_smt(client):
    client.post("/select-company", data={"company_id": "1"})


def _select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def test_index_renders_for_etf(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert resp.status_code == 200
    assert b"Beasiswa" in resp.data
    assert b"Ganti Company" not in resp.data


def test_index_shows_wrong_company_notice_for_smt(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/")
    assert resp.status_code == 200
    assert b"Ganti Company" in resp.data


def test_siswa_generate_kode_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/siswa/generate-kode?jenjang=S1&angkatan=2026")
    assert resp.status_code == 403


def test_siswa_tambah_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.post("/beasiswa/siswa/tambah", json={})
    assert resp.status_code == 403


def test_siswa_detail_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/siswa/S001")
    assert resp.status_code == 403


def test_budget_tambah_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.post("/beasiswa/budget/tambah", json={"code": "S001"})
    assert resp.status_code == 403


def test_payment_tambah_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.post("/beasiswa/payment/tambah", json={"code": "S001"})
    assert resp.status_code == 403


def test_klaim_tambah_multi_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.post("/beasiswa/klaim/tambah-multi", json={"rows": [{}]})
    assert resp.status_code == 403


def test_financial_summary_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/summary")
    assert resp.status_code == 403


def test_budget_export_csv_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/budget/export/csv")
    assert resp.status_code == 403


def test_rekap_data_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/rekap/data")
    assert resp.status_code == 403


def test_api_dashboard_summary_rejects_non_etf(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/api/dashboard/summary")
    assert resp.status_code == 403


def test_financial_summary_ok_for_etf(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/summary")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_vendor_list_api_not_gated_by_company(client):
    # `vendors` is a global lookup table, not scoped by company_id — it is
    # intentionally excluded from the ETF-only guard (see etf_company_required
    # docstring in modules/beasiswa/routes.py).
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/vendors")
    assert resp.status_code == 200
