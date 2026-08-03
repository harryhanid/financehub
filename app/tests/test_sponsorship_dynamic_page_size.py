from modules.sponsorship.service import seed_perusahaan, create_transaksi

COMPANY_ID = 1  # SMT


def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_smt(client):
    client.post("/select-company", data={"company_id": "1"})


def _seed(n):
    seed_perusahaan([("SMART", "AGRI", "AGRI")])
    for i in range(n):
        result = create_transaksi(COMPANY_ID, {
            "cat": "Sponsorship",
            "description": "Akademisi",
            "tanggal_form_sponsor": "2026-06-01",
            "cat1": "SMART",
            "lembaga_perorangan": f"Lembaga {i}",
            "amount_request": 1000000,
        })
        assert result["ok"] is True, result


def test_page_size_query_param_controls_slicing(client):
    login(client)
    _select_smt(client)
    _seed(3)
    resp = client.get("/sponsorship/data?page_size=2")
    assert resp.status_code == 200
    assert b"Halaman 1 dari 2" in resp.data


def test_page_size_defaults_when_absent(client):
    login(client)
    _select_smt(client)
    _seed(3)
    resp = client.get("/sponsorship/data")
    assert resp.status_code == 200
    assert b"budget-pagination" not in resp.data  # 3 rows < default 100, hidden


def test_page_size_ignores_invalid_values(client):
    login(client)
    _select_smt(client)
    _seed(3)
    resp = client.get("/sponsorship/data?page_size=abc")
    assert resp.status_code == 200


def test_page_size_clamped_to_max(client):
    login(client)
    _select_smt(client)
    _seed(3)
    resp = client.get("/sponsorship/data?page_size=99999")
    assert resp.status_code == 200
