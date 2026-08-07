# app/tests/test_sop_routes.py
from modules.sop.service import create_document


def login(client, username="admin", password="Admin@123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def test_index_requires_login(client):
    resp = client.get("/sop/")
    assert resp.status_code == 302


def test_index_renders_after_login(client):
    login(client)
    resp = client.get("/sop/")
    assert resp.status_code == 200


def test_index_lists_created_documents(client):
    login(client)
    create_document(modul="procurement", nama="SOP Master Vendor", kode="1")
    resp = client.get("/sop/")
    assert b"SOP Master Vendor" in resp.data


def test_index_filters_by_modul(client):
    login(client)
    create_document(modul="procurement", nama="SOP Hanya Procurement", kode="1")
    create_document(modul="finance-payment", nama="SOP Hanya Finance", kode="1")
    resp = client.get("/sop/?modul=procurement")
    assert b"SOP Hanya Procurement" in resp.data
    assert b"SOP Hanya Finance" not in resp.data


def test_index_search_by_nama(client):
    login(client)
    create_document(modul="it-operations", nama="SOP Zoom Meeting", kode="3")
    resp = client.get("/sop/?q=zoom")
    assert b"SOP Zoom Meeting" in resp.data
