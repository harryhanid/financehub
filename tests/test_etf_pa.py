# tests/test_etf_pa.py
import sqlite3 as _sq
import pytest


def _make_db(path):
    conn = _sq.connect(path)
    conn.execute("""
        CREATE TABLE siswa (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            code TEXT,
            nama TEXT,
            status TEXT,
            universitas TEXT,
            angkatan INTEGER,
            angkatan_kuliah TEXT,
            jenjang TEXT,
            program TEXT,
            fakultas TEXT,
            prodi TEXT,
            ipk_sem1 REAL, ipk_sem2 REAL, ipk_sem3 REAL, ipk_sem4 REAL,
            ipk_sem5 REAL, ipk_sem6 REAL, ipk_sem7 REAL, ipk_sem8 REAL,
            ipk_sem9 REAL, ipk_sem10 REAL
        )
    """)
    conn.execute("""
        CREATE TABLE etf_pa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            pa_number TEXT,
            tgl_payment_application TEXT,
            tgl_surat_pengajuan TEXT,
            doc_received_by_educ TEXT,
            received_pa_from_educ TEXT,
            checked_by_fincon TEXT,
            approved_by_htj_1 TEXT,
            send_pa_back_to_educ TEXT,
            pa_received_by_po_fin TEXT,
            approval_by_htj_2 TEXT,
            nomor_pam TEXT,
            tanggal_bayar TEXT,
            keterangan TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE etf_pa_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pa_id INTEGER,
            student_id INTEGER,
            jenis_pembayaran TEXT,
            semester TEXT,
            tahun_ajaran TEXT,
            ipk_sem_sebelumnya REAL DEFAULT 0,
            jumlah_pembayaran REAL DEFAULT 0
        )
    """)
    # Seed: 1 siswa, 3 PA with different statuses
    conn.execute("INSERT INTO siswa VALUES (1,1,'S001','Budi','active','Univ A',2020,'2020',\
'S1','Teknik','FT','IF',3.5,3.6,0,0,0,0,0,0,0,0)")
    conn.execute("INSERT INTO etf_pa (id,company_id,pa_number,status,created_at) VALUES (1,1,'PA/ETF/001/2026','open','2026-01-01')")
    conn.execute("INSERT INTO etf_pa (id,company_id,pa_number,status,created_at) VALUES (2,1,'PA/ETF/002/2026','on_process','2026-01-02')")
    conn.execute("INSERT INTO etf_pa (id,company_id,pa_number,status,created_at) VALUES (3,1,'PA/ETF/003/2026','complete','2026-01-03')")
    conn.execute("INSERT INTO etf_pa_lines (pa_id,student_id,jenis_pembayaran,semester,tahun_ajaran,jumlah_pembayaran) VALUES (1,1,'UKT','1','2024/2025',5000000)")
    conn.execute("INSERT INTO etf_pa_lines (pa_id,student_id,jenis_pembayaran,semester,tahun_ajaran,jumlah_pembayaran) VALUES (2,1,'UKT','2','2024/2025',5000000)")
    conn.execute("INSERT INTO etf_pa_lines (pa_id,student_id,jenis_pembayaran,semester,tahun_ajaran,jumlah_pembayaran) VALUES (3,1,'UKT','3','2024/2025',5000000)")
    conn.commit()
    conn.close()
    return path


def _fake_conn_factory(db_path):
    def _fake():
        c = _sq.connect(db_path)
        c.row_factory = _sq.Row
        return c
    return _fake


def test_get_pa_flat_active_returns_open_and_on_process(monkeypatch, tmp_path):
    db_path = str(tmp_path / "t.db")
    _make_db(db_path)
    from app.modules.etf_payment_application import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db_path))
    rows = svc.get_pa_flat(1, "agri", "active")
    statuses = {r["status"] for r in rows}
    assert "open" in statuses
    assert "on_process" in statuses
    assert "complete" not in statuses


def test_get_pa_flat_active_excludes_complete(monkeypatch, tmp_path):
    db_path = str(tmp_path / "t.db")
    _make_db(db_path)
    from app.modules.etf_payment_application import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db_path))
    rows = svc.get_pa_flat(1, "agri", "active")
    assert all(r["status"] != "complete" for r in rows)


def test_get_pa_flat_no_filter_returns_all(monkeypatch, tmp_path):
    db_path = str(tmp_path / "t.db")
    _make_db(db_path)
    from app.modules.etf_payment_application import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db_path))
    rows = svc.get_pa_flat(1, "agri", "")
    statuses = {r["status"] for r in rows}
    assert statuses == {"open", "on_process", "complete"}


def test_update_pa_updates_line_fields(monkeypatch, tmp_path):
    db_path = str(tmp_path / "t.db")
    _make_db(db_path)
    from app.modules.etf_payment_application import service as svc
    monkeypatch.setattr(svc, "get_conn", _fake_conn_factory(db_path))

    # Get the line_id of PA 1
    conn = _sq.connect(db_path)
    line_id = conn.execute("SELECT id FROM etf_pa_lines WHERE pa_id=1").fetchone()[0]
    conn.close()

    result = svc.update_pa(1, 1, {
        "tgl_payment_application": "2026-06-01",
        "tgl_surat_pengajuan": "",
        "doc_received_by_educ": "",
        "received_pa_from_educ": "",
        "checked_by_fincon": "",
        "approved_by_htj_1": "",
        "send_pa_back_to_educ": "",
        "pa_received_by_po_fin": "",
        "approval_by_htj_2": "",
        "nomor_pam": "",
        "tanggal_bayar": "",
        "keterangan": "",
        "status": "open",
        "line_id": line_id,
        "jenis_pembayaran": "Biaya Hidup",
        "semester": "3",
        "tahun_ajaran": "2025/2026",
        "ipk_sem_sebelumnya": 3.75,
        "jumlah_pembayaran": 9999999,
    }, "agri")

    assert result["ok"] is True

    conn2 = _sq.connect(db_path)
    line = conn2.execute("SELECT * FROM etf_pa_lines WHERE id=?", (line_id,)).fetchone()
    conn2.close()
    assert line[3] == "Biaya Hidup"   # jenis_pembayaran
    assert line[4] == "3"             # semester
    assert line[5] == "2025/2026"     # tahun_ajaran
    assert float(line[6]) == 3.75     # ipk_sem_sebelumnya
    assert float(line[7]) == 9999999  # jumlah_pembayaran
