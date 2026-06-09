# tests/test_pam_pa_cascade.py
"""Tests for PA status cascade triggered by set_memo_tanggal_bayar and cancel_pam_record."""
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_cascade.db")

from datetime import datetime
from database import init_db, get_conn
from modules.payment_memo.service import set_memo_tanggal_bayar, cancel_pam_record

COMPANY_ID = 2
COMPANY_CODE = "ETF"


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def _ts():
    return datetime.now().isoformat(timespec="seconds")


def _insert_siswa(conn) -> int:
    conn.execute(
        """INSERT INTO siswa
           (company_id, code, nama, jenjang, angkatan, program, fakultas, universitas, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "1250001", "Budi", "S1", 2025, "SMART", "Teknik", "UI", "Aktif")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    return sid


def _insert_pa(conn, pa_tbl, lines_tbl, pa_prefix, siswa_id, status="on_process"):
    """Insert one PA header + one line. Returns (pa_id, line_id)."""
    cur = conn.execute(
        f"INSERT INTO {pa_tbl} (company_id, pa_number, tgl_payment_application, status, created_at)"
        f" VALUES (?,?,?,?,?)",
        (COMPANY_ID, f"PA/{pa_prefix}/001/2026", "2026-06-01", status, _ts())
    )
    pa_id = cur.lastrowid
    cur2 = conn.execute(
        f"INSERT INTO {lines_tbl} (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran)"
        f" VALUES (?,?,?,?)",
        (pa_id, siswa_id, "By Pendidikan", 5000000)
    )
    line_id = cur2.lastrowid
    conn.commit()
    return pa_id, line_id


def _insert_memo_and_payment(conn, line_id):
    """Insert payment_memo + payment_beasiswa linked to line_id. Returns memo_id."""
    conn.execute(
        "INSERT INTO payment_memo (company_id, memo_number, status) VALUES (?,?,?)",
        (COMPANY_ID, "PAM/ETF/2026/001", "on_process")
    )
    memo_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, memo_id, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'on_process')""",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 3",
         "2026-06-01", 5000000, "AGRI", "PT. SMART Tbk", memo_id, line_id)
    )
    conn.commit()
    return memo_id


# ── tanggal_bayar cascade tests ──────────────────────────────────────────────

def test_tanggal_bayar_cascades_to_etf_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "etf_pa", "etf_pa_lines", "ETF", sid)
    memo_id = _insert_memo_and_payment(conn, line_id)
    conn.close()

    result = set_memo_tanggal_bayar(memo_id, "2026-06-15", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute("SELECT status, tanggal_bayar FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert row["status"] == "complete"
    assert row["tanggal_bayar"] == "2026-06-15"


def test_tanggal_bayar_cascades_to_app_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "app_pa", "app_pa_lines", "APP", sid)
    memo_id = _insert_memo_and_payment(conn, line_id)
    conn.close()

    result = set_memo_tanggal_bayar(memo_id, "2026-06-15", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute("SELECT status, tanggal_bayar FROM app_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert row["status"] == "complete", f"app_pa.status expected 'complete', got '{row['status']}'"
    assert row["tanggal_bayar"] == "2026-06-15"


def test_tanggal_bayar_cascades_to_sml_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "sml_pa", "sml_pa_lines", "SML", sid)
    memo_id = _insert_memo_and_payment(conn, line_id)
    conn.close()

    result = set_memo_tanggal_bayar(memo_id, "2026-06-15", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute("SELECT status, tanggal_bayar FROM sml_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert row["status"] == "complete", f"sml_pa.status expected 'complete', got '{row['status']}'"
    assert row["tanggal_bayar"] == "2026-06-15"


# ── cancel_pam_record revert tests ──────────────────────────────────────────

def _insert_pam_and_link(conn, pa_tbl, lines_tbl, pa_id, line_id):
    """Insert pam_records + payment_beasiswa with PAM link. Returns (pam_id, pam_no)."""
    pam_no = "PAM-001-ETF-06-2026"
    cur = conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, total_amount, status, created_at)
           VALUES (?,?,?,?,?,?)""",
        (COMPANY_ID, pam_no, "2026-06-08", 5000000, "open", _ts())
    )
    pam_id = cur.lastrowid
    conn.execute(
        f"UPDATE {pa_tbl} SET nomor_pam=?, status='on_process' WHERE id=?",
        (pam_no, pa_id)
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, pam, etf_pa_line_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'open')""",
        (COMPANY_ID, "1250001", "By Pendidikan", "Semester 3",
         "2026-06-01", 5000000, "AGRI", "PT. SMART Tbk", pam_no, line_id)
    )
    conn.commit()
    return pam_id, pam_no


def test_cancel_pam_reverts_etf_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "etf_pa", "etf_pa_lines", "ETF", sid, "on_process")
    pam_id, _ = _insert_pam_and_link(conn, "etf_pa", "etf_pa_lines", pa_id, line_id)
    conn.close()

    result = cancel_pam_record(pam_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute("SELECT status, nomor_pam FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert row["status"] == "open"
    assert row["nomor_pam"] is None


def test_cancel_pam_reverts_app_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "app_pa", "app_pa_lines", "APP", sid, "on_process")
    pam_id, _ = _insert_pam_and_link(conn, "app_pa", "app_pa_lines", pa_id, line_id)
    conn.close()

    result = cancel_pam_record(pam_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute("SELECT status, nomor_pam FROM app_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert row["status"] == "open", f"app_pa.status expected 'open', got '{row['status']}'"
    assert row["nomor_pam"] is None


def test_cancel_pam_reverts_sml_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "sml_pa", "sml_pa_lines", "SML", sid, "on_process")
    pam_id, _ = _insert_pam_and_link(conn, "sml_pa", "sml_pa_lines", pa_id, line_id)
    conn.close()

    result = cancel_pam_record(pam_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute("SELECT status, nomor_pam FROM sml_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert row["status"] == "open", f"sml_pa.status expected 'open', got '{row['status']}'"
    assert row["nomor_pam"] is None
