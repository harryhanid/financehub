def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def test_index_requires_login(client):
    resp = client.get("/bank/")
    assert resp.status_code == 302


def test_index_renders_after_login(client):
    login(client)
    _select_etf(client)
    resp = client.get("/bank/")
    assert resp.status_code == 200
    assert b"Bank Sahabat ETF" in resp.data
