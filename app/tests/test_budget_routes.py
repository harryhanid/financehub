# tests/test_budget_routes.py
import json


def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _create_releaser(client):
    login(client)
    client.post("/users/add", json={
        "username": "releaser1", "password": "Releaser@123", "role": "releaser",
    })


def test_master_list_requires_login(client):
    resp = client.get("/budget/master")
    assert resp.status_code == 302


def test_master_list_renders_after_login(client):
    login(client)
    resp = client.get("/budget/master")
    assert resp.status_code == 200


def test_master_create_and_get(client):
    login(client)
    resp = client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026,
        "budget_category": "OpEx", "activity": "Audit Fee", "amount": 1000000,
    })
    data = resp.get_json()
    assert data["ok"] is True
    budget_id = data["id"]

    get_resp = client.get(f"/budget/master/{budget_id}")
    fetched = get_resp.get_json()
    assert fetched["ok"] is True
    assert fetched["budget"]["company"] == "PO"


def test_master_update_via_route(client):
    login(client)
    created = client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000000,
    }).get_json()
    resp = client.post(f"/budget/master/{created['id']}/update", json={"amount": 2000000})
    assert resp.get_json()["ok"] is True

    fetched = client.get(f"/budget/master/{created['id']}").get_json()
    assert fetched["budget"]["amount"] == 2000000


def test_master_delete_requires_releaser_role(client):
    login(client)
    created = client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000000,
    }).get_json()
    # default seeded admin has role='releaser', so this should succeed
    resp = client.post(f"/budget/master/{created['id']}/delete")
    assert resp.get_json()["ok"] is True


def test_realisasi_list_requires_login(client):
    resp = client.get("/budget/realisasi")
    assert resp.status_code == 302


def test_realisasi_create_via_route(client):
    login(client)
    budget = client.post("/budget/master/create", json={
        "company": "TF", "dept": "IT", "mm": 2, "yy": 2026, "amount": 1000000,
    }).get_json()
    resp = client.post("/budget/realisasi/create", json={
        "budget_id": budget["id"], "amount": 300000, "tanggal_realisasi": "2026-02-05",
    })
    data = resp.get_json()
    assert data["ok"] is True
    assert data["trx_id"].startswith("TRX-")


def test_realisasi_update_and_delete_via_route(client):
    login(client)
    budget = client.post("/budget/master/create", json={
        "company": "TF", "dept": "IT", "mm": 2, "yy": 2026, "amount": 1000000,
    }).get_json()
    created = client.post("/budget/realisasi/create", json={
        "budget_id": budget["id"], "amount": 300000, "tanggal_realisasi": "2026-02-05",
    }).get_json()
    update_resp = client.post(f"/budget/realisasi/{created['trx_id']}/update", json={"amount": 400000})
    assert update_resp.get_json()["ok"] is True
    delete_resp = client.post(f"/budget/realisasi/{created['trx_id']}/delete")
    assert delete_resp.get_json()["ok"] is True


def test_dashboard_index_requires_login(client):
    resp = client.get("/budget/")
    assert resp.status_code == 302


def test_dashboard_index_renders(client):
    login(client)
    resp = client.get("/budget/")
    assert resp.status_code == 200


def test_dashboard_api_returns_expected_keys(client):
    login(client)
    client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000000,
    })
    resp = client.get("/budget/api/dashboard-data?year=2026")
    data = resp.get_json()
    assert "summary" in data
    assert "monthlyChart" in data


def test_lookups_api_returns_lists(client):
    login(client)
    client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026,
        "budget_category": "OpEx", "activity": "Audit Fee", "amount": 1000000,
    })
    resp = client.get("/budget/api/lookups")
    data = resp.get_json()
    assert "Finance" in data["departments"]
    assert "OpEx" in data["categories"]


def test_carryover_page_requires_login(client):
    resp = client.get("/budget/carryover")
    assert resp.status_code == 302


def test_carryover_request_and_approve_flow(client):
    login(client)
    budget = client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000000,
    }).get_json()

    req_resp = client.post("/budget/carryover/request", json={
        "budget_id": budget["id"], "reason": "Belum sempat realisasi",
    })
    assert req_resp.get_json()["ok"] is True

    # seeded admin has role='releaser', so approval succeeds without a separate releaser account
    approve_resp = client.post(f"/budget/carryover/{budget['id']}/approve", json={"extension_months": 6})
    assert approve_resp.get_json()["ok"] is True


def test_additional_budget_request_and_approve_flow(client):
    login(client)
    budget = client.post("/budget/master/create", json={
        "company": "TF", "dept": "IT", "mm": 1, "yy": 2026, "amount": 1000000,
    }).get_json()

    req_resp = client.post("/budget/additional/request", json={
        "budget_id": budget["id"], "amount": 500000, "reason": "Butuh tambahan",
    })
    assert req_resp.get_json()["ok"] is True

    approve_resp = client.post(f"/budget/additional/{budget['id']}/approve", json={"extension_months": 3})
    assert approve_resp.get_json()["ok"] is True


def test_carryover_reject_flow(client):
    login(client)
    budget = client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000000,
    }).get_json()
    client.post("/budget/carryover/request", json={"budget_id": budget["id"], "reason": "reason"})
    reject_resp = client.post(f"/budget/carryover/{budget['id']}/reject", json={"reason": "Tidak sesuai"})
    assert reject_resp.get_json()["ok"] is True


def test_export_transactions_route_downloads_csv(client):
    login(client)
    client.post("/budget/master/create", json={
        "company": "PO", "dept": "Finance", "mm": 1, "yy": 2026, "amount": 1000000,
    })
    resp = client.get("/budget/export/transactions?year=2026")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/csv")


def test_export_invalid_report_type_returns_400(client):
    login(client)
    resp = client.get("/budget/export/not-a-real-report")
    assert resp.status_code == 400


def test_nav_shows_budget_link_after_company_selection(client):
    login(client)
    client.post("/select-company", data={"company_id": "2"})
    resp = client.get("/dashboard")
    assert b"/budget/" in resp.data
