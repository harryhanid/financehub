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


def test_read_page_shows_placeholder_when_file_missing_on_disk(client):
    login(client)
    doc_id = create_document(modul="procurement", nama="SOP File Hilang", kode="2",
                              file_path="procurement/2-tidak-ada.docx")
    resp = client.get(f"/sop/{doc_id}")
    assert resp.status_code == 200
    assert b"File tidak ditemukan di storage" in resp.data


def test_download_returns_the_uploaded_file(client):
    login(client)
    _write_sample_docx("procurement/1-download-uji.docx")
    doc_id = create_document(modul="procurement", nama="SOP Download Uji", kode="1",
                              file_path="procurement/1-download-uji.docx")
    resp = client.get(f"/sop/{doc_id}/download")
    assert resp.status_code == 200
    assert resp.headers["Content-Disposition"].startswith("attachment")


def test_download_redirects_for_belum_dibuat(client):
    login(client)
    doc_id = create_document(modul="hr-personnel", nama="SOP Tanpa File", status="belum_dibuat")
    resp = client.get(f"/sop/{doc_id}/download")
    assert resp.status_code == 302


def test_download_redirects_when_file_missing_on_disk(client):
    login(client)
    doc_id = create_document(modul="procurement", nama="SOP Download Hilang", kode="3",
                              status="aktif", file_path="procurement/3-tidak-ada.docx")
    resp = client.get(f"/sop/{doc_id}/download")
    assert resp.status_code == 302


from io import BytesIO


def test_upload_replaces_file_and_records_history(client):
    login(client)
    _write_sample_docx("procurement/1-upload-uji.docx")
    doc_id = create_document(modul="procurement", nama="SOP Upload Uji", kode="1",
                              file_path="procurement/1-upload-uji.docx")

    new_doc = docx.Document()
    new_doc.add_heading("SOP Upload Uji", level=0)
    new_doc.add_heading("1. Tujuan", level=1)
    new_doc.add_paragraph("⚠ [PERLU VERIFIKASI: nominal baru]")
    buf = BytesIO()
    new_doc.save(buf)
    buf.seek(0)

    resp = client.post(
        f"/sop/{doc_id}/upload",
        data={"file": (buf, "1-upload-uji.docx")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302

    from modules.sop.service import get_document
    updated = get_document(doc_id)
    assert updated["perlu_verifikasi_count"] == 1
    assert updated["uploaded_by"] == "admin"

    conn_check = client.get(f"/sop/{doc_id}")
    assert b"nominal baru" in conn_check.data


def test_upload_rejects_non_docx_file(client):
    login(client)
    _write_sample_docx("procurement/1-reject-uji.docx")
    doc_id = create_document(modul="procurement", nama="SOP Reject Uji", kode="1",
                              file_path="procurement/1-reject-uji.docx")
    resp = client.post(
        f"/sop/{doc_id}/upload",
        data={"file": (BytesIO(b"not a docx"), "file.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302
    from modules.sop.service import get_document
    unchanged = get_document(doc_id)
    assert unchanged["file_path"] == "procurement/1-reject-uji.docx"


def _make_docx_bytes(heading="SOP Upload Baru"):
    new_doc = docx.Document()
    new_doc.add_heading(heading, level=0)
    new_doc.add_heading("1. Tujuan", level=1)
    new_doc.add_paragraph("Tujuan upload baru.")
    buf = BytesIO()
    new_doc.save(buf)
    buf.seek(0)
    return buf


def test_upload_first_time_to_belum_dibuat_document_activates_it(client):
    login(client)
    doc_id = create_document(modul="hr-personnel", nama="SOP Belum Ada Upload",
                              status="belum_dibuat", catatan="Tidak ada sumber")

    resp = client.post(
        f"/sop/{doc_id}/upload",
        data={"file": (_make_docx_bytes(), "sop-baru.docx")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302

    from modules.sop.service import get_document
    updated = get_document(doc_id)
    assert updated["status"] == "aktif"
    assert updated["file_path"] is not None

    saved_path = os.path.join(config.SOP_STORAGE_DIR, updated["file_path"])
    assert os.path.exists(saved_path)
    assert os.path.dirname(os.path.abspath(saved_path)) == os.path.abspath(
        os.path.join(config.SOP_STORAGE_DIR, "hr-personnel")
    )


def test_upload_first_time_rejects_path_traversal_filename(client):
    login(client)
    doc_id = create_document(modul="procurement", nama="SOP Traversal Uji",
                              status="belum_dibuat")

    modul_dir = os.path.join(config.SOP_STORAGE_DIR, "procurement")
    resp = client.post(
        f"/sop/{doc_id}/upload",
        data={"file": (_make_docx_bytes(), "../../../evil.docx")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302

    # No file should ever land outside SOP_STORAGE_DIR / modul_dir.
    outside_path = os.path.join(os.path.dirname(os.path.abspath(config.SOP_STORAGE_DIR)), "evil.docx")
    assert not os.path.exists(outside_path)

    from modules.sop.service import get_document
    updated = get_document(doc_id)
    if updated["file_path"]:
        saved_path = os.path.join(config.SOP_STORAGE_DIR, updated["file_path"])
        abs_saved = os.path.abspath(saved_path)
        abs_modul_dir = os.path.abspath(modul_dir)
        assert os.path.commonpath([abs_saved, abs_modul_dir]) == abs_modul_dir
        saved_name = os.path.basename(saved_path)
        assert ".." not in saved_name
        assert "/" not in saved_name and "\\" not in saved_name


def test_upload_revision_keeps_original_filename_ignoring_new_upload_name(client):
    login(client)
    _write_sample_docx("procurement/1-existing.docx")
    doc_id = create_document(modul="procurement", nama="SOP Revisi Uji", kode="1",
                              file_path="procurement/1-existing.docx")

    resp = client.post(
        f"/sop/{doc_id}/upload",
        data={"file": (_make_docx_bytes(), "totally-different-name.docx")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302

    from modules.sop.service import get_document
    updated = get_document(doc_id)
    assert updated["file_path"] == "procurement/1-existing.docx"

    modul_dir = os.path.join(config.SOP_STORAGE_DIR, "procurement")
    assert os.path.exists(os.path.join(modul_dir, "1-existing.docx"))
    assert not os.path.exists(os.path.join(modul_dir, "totally-different-name.docx"))
