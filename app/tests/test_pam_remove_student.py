"""Tests for remove_student_from_pam — single-row removal from Open PAM."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_remove_student.db")

import pytest
from datetime import datetime
from database import init_db, get_conn
from modules.payment_memo.service import remove_student_from_pam

COMPANY_ID = 2


def _remove_db(path):
    """Remove DB and WAL/SHM sidecar files, best-effort."""
    import sqlite3 as _sqlite3
    for ext in ("", "-wal", "-shm"):
        p = path + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except PermissionError:
                pass


@pytest.fixture(autouse=True)
def clean_db(tmp_path):
    # Use a per-test temp directory so each test gets a fresh, isolated DB
    db_path = str(tmp_path / "test_remove_student.db")
    config.DB_PATH = db_path
    init_db()
    yield
    _remove_db(db_path)


def _ts():
    return datetime.now().isoformat(timespec="seconds")


def _insert_siswa(conn, code="1250001") -> int:
    conn.execute(
        """INSERT INTO siswa
           (company_id, code, nama, jenjang, angkatan, program, fakultas, universitas, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, code, f"Siswa {code}", "S1", 2025, "SMART", "Teknik", "UI", "Aktif")
    )
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    return row_id


def _insert_pam(conn, pam_no="PAM-ETF-06-2026-001", total=5_000_000, status="open") -> int:
    """Insert pam_records, return pam_no string (used as FK in payment_beasiswa)."""
    conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, total_amount, pillar, source, status, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, pam_no, "2026-06-08", total, "AGRI", "beasiswa", status, _ts())
    )
    conn.commit()
    return pam_no


def _insert_etf_pa_with_line(conn, pa_number="PA/ETF/001/2026", pam_no=None, siswa_id=None) -> tuple:
    """Insert etf_pa + etf_pa_lines. Returns (pa_id, line_id)."""
    cur = conn.execute(
        """INSERT INTO etf_pa
           (company_id, pa_number, tgl_payment_application, status, nomor_pam, created_at)
           VALUES (?,?,?,?,?,?)""",
        (COMPANY_ID, pa_number, "2026-06-01", "on_process", pam_no, _ts())
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        """INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran)
           VALUES (?,?,?,?)""",
        (pa_id, siswa_id, "By Pendidikan", 5_000_000)
    )
    line_id = cur2.lastrowid
    conn.commit()
    return pa_id, line_id


def _insert_payment_beasiswa(conn, pam_no, line_id, siswa_code="1250001", amount=5_000_000) -> int:
    """Insert payment_beasiswa linked to a pam and etf_pa_line. Returns payment_beasiswa id."""
    cur = conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, pam, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'open')""",
        (COMPANY_ID, siswa_code, "By Pendidikan", "Semester 3",
         "2026-06-01", amount, "AGRI", "PT. SMART Tbk", pam_no, line_id)
    )
    pb_id = cur.lastrowid
    conn.commit()
    return pb_id


# ─────────────────────────────────────────────────────────────────────────────


def test_remove_one_of_many_students():
    """Remove 1 siswa dari PAM yang punya 3 siswa:
    - payment_beasiswa row terhapus
    - pam_records.total_amount direcalculate ke 10jt (sisa 2 siswa × 5jt)
    - etf_pa siswa tersebut di-revert ke open + nomor_pam=NULL
    - 2 siswa lain tidak berubah
    """
    conn = get_conn()
    sid1 = _insert_siswa(conn, "1250001")
    sid2 = _insert_siswa(conn, "1250002")
    sid3 = _insert_siswa(conn, "1250003")
    pam_no = _insert_pam(conn, total=15_000_000)

    pa1_id, line1_id = _insert_etf_pa_with_line(conn, "PA/ETF/001/2026", pam_no, sid1)
    pa2_id, line2_id = _insert_etf_pa_with_line(conn, "PA/ETF/002/2026", pam_no, sid2)
    pa3_id, line3_id = _insert_etf_pa_with_line(conn, "PA/ETF/003/2026", pam_no, sid3)

    pb1_id = _insert_payment_beasiswa(conn, pam_no, line1_id, "1250001")
    _insert_payment_beasiswa(conn, pam_no, line2_id, "1250002")
    _insert_payment_beasiswa(conn, pam_no, line3_id, "1250003")
    conn.close()

    result = remove_student_from_pam(pb1_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    # payment_beasiswa row terhapus
    pb = conn.execute("SELECT id FROM payment_beasiswa WHERE id=?", (pb1_id,)).fetchone()
    assert pb is None, "payment_beasiswa row seharusnya terhapus"

    # pam_records total diupdate ke 10jt
    pam = conn.execute("SELECT total_amount, status FROM pam_records WHERE pam_no=? AND company_id=?",
                       (pam_no, COMPANY_ID)).fetchone()
    assert pam is not None, "pam_records seharusnya masih ada"
    assert pam["total_amount"] == 10_000_000, f"total_amount expected 10000000, got {pam['total_amount']}"
    assert pam["status"] == "open"

    # PA siswa 1 di-revert
    pa1 = conn.execute("SELECT status, nomor_pam FROM etf_pa WHERE id=?", (pa1_id,)).fetchone()
    assert pa1["status"] == "open", f"etf_pa 1 status expected 'open', got '{pa1['status']}'"
    assert pa1["nomor_pam"] is None

    # PA siswa 2 dan 3 tidak berubah
    pa2 = conn.execute("SELECT status, nomor_pam FROM etf_pa WHERE id=?", (pa2_id,)).fetchone()
    assert pa2["status"] == "on_process"
    pa3 = conn.execute("SELECT status, nomor_pam FROM etf_pa WHERE id=?", (pa3_id,)).fetchone()
    assert pa3["status"] == "on_process"
    conn.close()


def test_remove_last_student_deletes_pam():
    """Remove siswa terakhir dalam PAM:
    - payment_beasiswa row terhapus
    - pam_records entry ikut terhapus (tidak ada sisa)
    - etf_pa di-revert ke open
    """
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_no = _insert_pam(conn, total=5_000_000)
    pa_id, line_id = _insert_etf_pa_with_line(conn, "PA/ETF/001/2026", pam_no, sid)
    pb_id = _insert_payment_beasiswa(conn, pam_no, line_id)
    conn.close()

    result = remove_student_from_pam(pb_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    # payment_beasiswa terhapus
    pb = conn.execute("SELECT id FROM payment_beasiswa WHERE id=?", (pb_id,)).fetchone()
    assert pb is None

    # pam_records ikut terhapus
    pam = conn.execute("SELECT id FROM pam_records WHERE pam_no=? AND company_id=?",
                       (pam_no, COMPANY_ID)).fetchone()
    assert pam is None, "pam_records seharusnya terhapus karena tidak ada sisa siswa"

    # etf_pa di-revert
    pa = conn.execute("SELECT status, nomor_pam FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    assert pa["status"] == "open"
    assert pa["nomor_pam"] is None
    conn.close()


def test_remove_blocked_if_pam_not_open():
    """Jika pam_records.status != 'open', operasi ditolak dan tidak ada perubahan DB."""
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_no = _insert_pam(conn, total=5_000_000, status="on_process")
    pa_id, line_id = _insert_etf_pa_with_line(conn, "PA/ETF/001/2026", pam_no, sid)
    pb_id = _insert_payment_beasiswa(conn, pam_no, line_id)
    conn.close()

    result = remove_student_from_pam(pb_id, COMPANY_ID)
    assert result["ok"] is False
    assert "sudah diproses" in result["pesan"] or "tidak dapat" in result["pesan"]

    conn = get_conn()
    # Tidak ada perubahan — payment_beasiswa masih ada
    pb = conn.execute("SELECT id FROM payment_beasiswa WHERE id=?", (pb_id,)).fetchone()
    assert pb is not None, "payment_beasiswa seharusnya tidak berubah"
    # pam_records masih ada dengan status on_process
    pam = conn.execute("SELECT status FROM pam_records WHERE pam_no=? AND company_id=?",
                       (pam_no, COMPANY_ID)).fetchone()
    assert pam["status"] == "on_process"
    conn.close()


def test_pa_not_reverted_if_has_other_payment():
    """Jika PA punya 2 line, dan line lain masih punya payment_beasiswa aktif,
    PA tidak di-revert saat salah satu payment dihapus."""
    conn = get_conn()
    sid1 = _insert_siswa(conn, "1250001")
    sid2 = _insert_siswa(conn, "1250002")
    pam_no_A = _insert_pam(conn, "PAM-ETF-06-2026-001", total=10_000_000)
    pam_no_B = _insert_pam(conn, "PAM-ETF-06-2026-002", total=5_000_000)

    # Satu PA dengan 2 line (sid1 dan sid2)
    cur = conn.execute(
        """INSERT INTO etf_pa
           (company_id, pa_number, tgl_payment_application, status, nomor_pam, created_at)
           VALUES (?,?,?,?,?,?)""",
        (COMPANY_ID, "PA/ETF/001/2026", "2026-06-01", "on_process", pam_no_A, _ts())
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid1, "By Pendidikan", 5_000_000)
    )
    line_A = cur2.lastrowid
    cur3 = conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid2, "By Pendidikan", 5_000_000)
    )
    line_B = cur3.lastrowid

    # Dua payment_beasiswa — line_A di PAM-A, line_B di PAM-B
    pb_A = _insert_payment_beasiswa(conn, pam_no_A, line_A, "1250001")
    _insert_payment_beasiswa(conn, pam_no_B, line_B, "1250002")
    conn.commit()
    conn.close()

    # Hapus payment siswa line_A dari PAM-A
    result = remove_student_from_pam(pb_A, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    # PA tidak di-revert: masih on_process karena line_B masih punya payment aktif
    pa = conn.execute("SELECT status, nomor_pam FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    assert pa["status"] == "on_process", \
        f"etf_pa status seharusnya tetap 'on_process', got '{pa['status']}'"
    conn.close()
