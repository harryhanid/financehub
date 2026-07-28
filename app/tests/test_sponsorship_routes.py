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


def test_input_page_renders_for_smt(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/input")
    assert resp.status_code == 200
    assert b"Input" in resp.data


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


def test_report_page_renders_placeholder(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/report")
    assert resp.status_code == 200
    assert b"akan datang" in resp.data.lower()


def test_dashboard_registered_in_nav_tabs():
    from modules.dashboard.routes import DASHBOARD_TABS
    keys = [t[2] for t in DASHBOARD_TABS]
    assert "sponsorship" in keys
