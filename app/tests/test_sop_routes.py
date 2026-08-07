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


import os
import docx
import config


def _write_sample_docx(rel_path):
    full_path = os.path.join(config.SOP_STORAGE_DIR, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    document = docx.Document()
    document.add_heading("SOP Baca Uji", level=0)
    document.add_heading("1. Tujuan", level=1)
    document.add_paragraph("Tujuan uji baca.", style="List Bullet")
    document.save(full_path)
    return full_path


def test_read_page_renders_parsed_content(client):
    login(client)
    _write_sample_docx("procurement/1-uji.docx")
    doc_id = create_document(modul="procurement", nama="SOP Baca Uji", kode="1",
                              file_path="procurement/1-uji.docx")
    resp = client.get(f"/sop/{doc_id}")
    assert resp.status_code == 200
    assert b"Tujuan uji baca." in resp.data


def test_read_page_shows_placeholder_for_belum_dibuat(client):
    login(client)
    doc_id = create_document(modul="hr-personnel", nama="SOP Belum Ada",
                              status="belum_dibuat", catatan="Tidak ada sumber")
    resp = client.get(f"/sop/{doc_id}")
    assert resp.status_code == 200
    assert b"Tidak ada sumber" in resp.data


def test_read_page_redirects_for_unknown_id(client):
    login(client)
    resp = client.get("/sop/999999")
    assert resp.status_code == 302
