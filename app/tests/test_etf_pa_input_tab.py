def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def test_input_tab_renders_form_sections(client):
    login(client)
    _select_etf(client)
    resp = client.get("/etf-payment-application/?tab=input")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "Buat Payment Application Baru" in html
    assert "Pilih Jenis PA" in html
    assert "Daftar Pembayaran" in html


def test_input_tab_has_energy(client):
    login(client)
    _select_etf(client)
    resp = client.get("/etf-payment-application/?tab=input")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'value="energy"' in html
    assert "EFIN" in html or "EFIN" in html
