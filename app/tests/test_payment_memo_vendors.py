# tests/test_payment_memo_vendors.py

def login(client):
    return client.post("/auth/login", json={"username": "admin", "password": "Admin@123"})


def select_etf(client):
    client.post("/select-company", data={"company_id": "2"})


def test_vendors_list_requires_login(client):
    """/vendors is a pure-JSON endpoint (decorated @json_required, not
    @jwt_html_required) — an unauthenticated request must get a JSON 401,
    not a 302 redirect to the login page. A redirect here would be silently
    followed by fetch()/apiFetch(), which would then try to parse the login
    page's HTML as JSON and fail (see the ipay/next-pam-no incident this
    was generalized from)."""
    resp = client.get("/payment-memo/vendors")
    assert resp.status_code == 401
    assert resp.get_json()["ok"] is False


def test_vendors_list_returns_rows(client):
    login(client)
    select_etf(client)
    resp = client.get("/payment-memo/vendors")
    data = resp.get_json()
    assert data["ok"] is True
    assert len(data["rows"]) > 0
    assert "id" in data["rows"][0]


def test_vendors_list_search_filters(client):
    login(client)
    select_etf(client)
    add = client.post("/payment-memo/vendors/add", json={"name": "PT Route Search Test", "pillar": "AGRI", "cost_center": ""})
    assert add.get_json()["ok"] is True
    resp = client.get("/payment-memo/vendors?search=Route Search")
    data = resp.get_json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["name"] == "PT Route Search Test"


def test_vendors_add_success(client):
    login(client)
    select_etf(client)
    resp = client.post("/payment-memo/vendors/add", json={"name": "PT Route Add Test", "pillar": "LAND", "cost_center": "1234C1POFF"})
    data = resp.get_json()
    assert data["ok"] is True
    assert "id" in data


def test_vendors_add_duplicate_rejected(client):
    login(client)
    select_etf(client)
    client.post("/payment-memo/vendors/add", json={"name": "PT Route Dup Test", "pillar": "AGRI", "cost_center": ""})
    resp = client.post("/payment-memo/vendors/add", json={"name": "PT Route Dup Test", "pillar": "APP", "cost_center": ""})
    data = resp.get_json()
    assert data["ok"] is False
    assert "sudah terdaftar" in data["pesan"]


def test_vendors_edit_success(client):
    login(client)
    select_etf(client)
    added = client.post("/payment-memo/vendors/add", json={"name": "PT Route Edit Test", "pillar": "APP", "cost_center": ""}).get_json()
    resp = client.post(f"/payment-memo/vendors/{added['id']}/edit", json={"name": "PT Route Edit Test Renamed", "pillar": "SETF", "cost_center": "9999C1POFF"})
    data = resp.get_json()
    assert data["ok"] is True
    list_resp = client.get("/payment-memo/vendors?search=Route Edit Test Renamed")
    rows = list_resp.get_json()["rows"]
    assert len(rows) == 1
    assert rows[0]["pillar"] == "SETF"


def test_vendors_edit_duplicate_rejected(client):
    login(client)
    select_etf(client)
    a = client.post("/payment-memo/vendors/add", json={"name": "PT Route Edit A", "pillar": "AGRI", "cost_center": ""}).get_json()
    client.post("/payment-memo/vendors/add", json={"name": "PT Route Edit B", "pillar": "AGRI", "cost_center": ""})
    resp = client.post(f"/payment-memo/vendors/{a['id']}/edit", json={"name": "PT Route Edit B", "pillar": "AGRI", "cost_center": ""})
    data = resp.get_json()
    assert data["ok"] is False
    assert "sudah terdaftar" in data["pesan"]
