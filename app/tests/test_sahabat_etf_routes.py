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
