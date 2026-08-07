import os
import docx
from modules.sop.service import (
    create_document, list_documents, get_document, record_upload,
    count_perlu_verifikasi_in_file,
)


def test_create_and_get_document():
    doc_id = create_document(modul="procurement", nama="SOP Master Vendor", kode="1")
    doc = get_document(doc_id)
    assert doc["modul"] == "procurement"
    assert doc["nama"] == "SOP Master Vendor"
    assert doc["status"] == "aktif"


def test_get_document_returns_none_for_missing_id():
    assert get_document(999999) is None


def test_list_documents_filters_by_modul():
    create_document(modul="procurement", nama="SOP A")
    create_document(modul="finance-payment", nama="SOP B")
    results = list_documents(modul="procurement")
    assert all(d["modul"] == "procurement" for d in results)
    assert any(d["nama"] == "SOP A" for d in results)
    assert not any(d["nama"] == "SOP B" for d in results)


def test_list_documents_filters_by_status():
    create_document(modul="hr-personnel", nama="SOP Belum", status="belum_dibuat")
    results = list_documents(status="belum_dibuat")
    assert all(d["status"] == "belum_dibuat" for d in results)


def test_list_documents_search_matches_nama_case_insensitive():
    create_document(modul="it-operations", nama="SOP Zoom Meeting")
    results = list_documents(search="zoom")
    assert any(d["nama"] == "SOP Zoom Meeting" for d in results)


def test_record_upload_updates_document_and_adds_history():
    doc_id = create_document(modul="procurement", nama="SOP Upload Test")
    record_upload(doc_id, "procurement/1-test.docx", 3, "tester", catatan="revisi awal")
    doc = get_document(doc_id)
    assert doc["file_path"] == "procurement/1-test.docx"
    assert doc["perlu_verifikasi_count"] == 3
    assert doc["uploaded_by"] == "tester"
    assert doc["uploaded_at"] is not None


def test_count_perlu_verifikasi_in_file(tmp_path):
    path = str(tmp_path / "contoh.docx")
    document = docx.Document()
    document.add_paragraph("Baris normal.")
    document.add_paragraph("Baris ⚠ [PERLU VERIFIKASI: ambang nominal].")
    table = document.add_table(rows=1, cols=1)
    table.rows[0].cells[0].text = "PERLU VERIFIKASI di tabel"
    document.save(path)
    assert count_perlu_verifikasi_in_file(path) == 2
