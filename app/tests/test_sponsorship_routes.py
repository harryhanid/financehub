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
