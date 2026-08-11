from database import get_conn


def test_sop_documents_table_exists():
    conn = get_conn()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sop_documents)")}
    conn.close()
    assert cols == {
        "id", "modul", "kode", "nama", "status", "perlu_verifikasi_count",
        "file_path", "catatan", "uploaded_by", "uploaded_at", "created_at",
    }


def test_sop_upload_history_table_exists():
    conn = get_conn()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sop_upload_history)")}
    conn.close()
    assert cols == {"id", "sop_id", "uploaded_by", "uploaded_at", "catatan"}


def test_sop_documents_status_defaults_to_aktif():
    conn = get_conn()
    conn.execute(
        "INSERT INTO sop_documents (modul, nama) VALUES ('procurement', 'SOP Uji')"
    )
    conn.commit()
    row = conn.execute("SELECT * FROM sop_documents WHERE nama='SOP Uji'").fetchone()
    conn.close()
    assert row["status"] == "aktif"


def test_sop_upload_history_references_sop_documents():
    conn = get_conn()
    conn.execute("INSERT INTO sop_documents (modul, nama) VALUES ('procurement', 'SOP Uji 2')")
    doc_id = conn.execute("SELECT id FROM sop_documents WHERE nama='SOP Uji 2'").fetchone()["id"]
    conn.execute(
        "INSERT INTO sop_upload_history (sop_id, uploaded_by) VALUES (?, 'tester')",
        (doc_id,),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM sop_upload_history WHERE sop_id=?", (doc_id,)).fetchone()
    conn.close()
    assert row["uploaded_by"] == "tester"
