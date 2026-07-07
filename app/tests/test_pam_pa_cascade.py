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


def test_cancel_pam_reverts_energy_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "energy_pa", "energy_pa_lines", "ENR", sid, "on_process")
    pam_id, _ = _insert_pam_and_link(conn, "energy_pa", "energy_pa_lines", pa_id, line_id)
    conn.close()

    result = cancel_pam_record(pam_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute("SELECT status, nomor_pam FROM energy_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert row["status"] == "open", f"energy_pa.status expected 'open', got '{row['status']}'"
    assert row["nomor_pam"] is None


def test_cancel_pam_reverts_setf_pa():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pa_id, line_id = _insert_pa(conn, "setf_pa", "setf_pa_lines", "SETF", sid, "on_process")
    pam_id, _ = _insert_pam_and_link(conn, "setf_pa", "setf_pa_lines", pa_id, line_id)
    conn.close()

    result = cancel_pam_record(pam_id, COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    row = conn.execute("SELECT status, nomor_pam FROM setf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()
    assert row["status"] == "open", f"setf_pa.status expected 'open', got '{row['status']}'"
    assert row["nomor_pam"] is None


# ── set_pam_complete_cascade tests ───────────────────────────────────────────

from modules.payment_memo.service import set_pam_complete_cascade


def _insert_pam_beasiswa(conn, pa_tbl, lines_tbl, pa_prefix, pillar, siswa_id):
    """Buat PA header + line + pam_records(source='beasiswa', pillar=pillar) + payment_beasiswa linked."""
    cur = conn.execute(
        f"INSERT INTO {pa_tbl} (company_id, pa_number, tgl_payment_application, status, created_at)"
        f" VALUES (?,?,?,?,?)",
        (COMPANY_ID, f"PA/{pa_prefix}/001/2026", "2026-06-01", "on_process", _ts())
    )
    pa_id   = cur.lastrowid
    cur2    = conn.execute(
        f"INSERT INTO {lines_tbl} (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran)"
        f" VALUES (?,?,?,?)",
        (pa_id, siswa_id, "By Pendidikan", 5_000_000)
    )
    line_id = cur2.lastrowid

    pam_no = f"PAM-{pa_prefix}-06-2026-001"
    cur3 = conn.execute(
        """INSERT INTO pam_records
           (company_id, pam_no, pam_date, total_amount, pillar, source, status, created_at)
           VALUES (?,?,?,?,?,'beasiswa','open',?)""",
        (COMPANY_ID, pam_no, "2026-06-08", 5_000_000, pillar, _ts())
    )
    pam_id = cur3.lastrowid

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
         "2026-06-01", 5_000_000, pillar, "PT. SMART Tbk", pam_no, line_id)
    )
    conn.commit()
    return pam_id, pa_id


def test_cascade_agri_beasiswa_sets_status_complete():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_id, pa_id = _insert_pam_beasiswa(conn, "etf_pa", "etf_pa_lines", "ETF", "AGRI", sid)
    conn.close()

    result = set_pam_complete_cascade(pam_id, "2026-06-20", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pb = conn.execute(
        "SELECT status FROM payment_beasiswa WHERE pam=?",
        ("PAM-ETF-06-2026-001",)
    ).fetchone()
    pa = conn.execute("SELECT status, tanggal_bayar FROM etf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()

    assert pb["status"] == "complete"
    assert pa["status"] == "complete"
    assert pa["tanggal_bayar"] == "2026-06-20"


def test_cascade_app_sets_tgl_paid_app():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_id, pa_id = _insert_pam_beasiswa(conn, "app_pa", "app_pa_lines", "APP", "APP", sid)
    conn.close()

    result = set_pam_complete_cascade(pam_id, "2026-06-20", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pb = conn.execute(
        "SELECT status, tgl_Paid_APP FROM payment_beasiswa WHERE pam=?",
        ("PAM-APP-06-2026-001",)
    ).fetchone()
    pa = conn.execute("SELECT status, tanggal_bayar FROM app_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()

    assert pb["status"] == "complete"
    assert pb["tgl_Paid_APP"] == "2026-06-20"
    assert pa["status"] == "complete"
    assert pa["tanggal_bayar"] == "2026-06-20"


def test_cascade_land_sets_tgl_paid_land():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_id, pa_id = _insert_pam_beasiswa(conn, "sml_pa", "sml_pa_lines", "SML", "LAND", sid)
    conn.close()

    result = set_pam_complete_cascade(pam_id, "2026-06-20", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pb = conn.execute(
        "SELECT status, tgl_Paid_LAND FROM payment_beasiswa WHERE pam=?",
        ("PAM-SML-06-2026-001",)
    ).fetchone()
    pa = conn.execute("SELECT status, tanggal_bayar FROM sml_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()

    assert pb["status"] == "complete"
    assert pb["tgl_Paid_LAND"] == "2026-06-20"
    assert pa["status"] == "complete"
    assert pa["tanggal_bayar"] == "2026-06-20"


def test_cascade_energy_sets_tgl_paid_energy():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_id, pa_id = _insert_pam_beasiswa(conn, "energy_pa", "energy_pa_lines", "ENR", "ENERGY", sid)
    conn.close()

    result = set_pam_complete_cascade(pam_id, "2026-06-20", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pb = conn.execute(
        "SELECT status, tgl_Paid_ENERGY FROM payment_beasiswa WHERE pam=?",
        ("PAM-ENR-06-2026-001",)
    ).fetchone()
    pa = conn.execute("SELECT status, tanggal_bayar FROM energy_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()

    assert pb["status"] == "complete"
    assert pb["tgl_Paid_ENERGY"] == "2026-06-20"
    assert pa["status"] == "complete"
    assert pa["tanggal_bayar"] == "2026-06-20"


def test_cascade_setf_sets_tgl_paid_setf():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_id, pa_id = _insert_pam_beasiswa(conn, "setf_pa", "setf_pa_lines", "SETF", "SETF", sid)
    conn.close()

    result = set_pam_complete_cascade(pam_id, "2026-06-20", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pb = conn.execute(
        "SELECT status, tgl_Paid_SETF FROM payment_beasiswa WHERE pam=?",
        ("PAM-SETF-06-2026-001",)
    ).fetchone()
    pa = conn.execute("SELECT status, tanggal_bayar FROM setf_pa WHERE id=?", (pa_id,)).fetchone()
    conn.close()

    assert pb["status"] == "complete"
    assert pb["tgl_Paid_SETF"] == "2026-06-20"
    assert pa["status"] == "complete"
    assert pa["tanggal_bayar"] == "2026-06-20"


# ── schema tests ─────────────────────────────────────────────────────────────

def test_payment_beasiswa_has_tgl_paid_columns():
    conn = get_conn()
    cols = [row[1] for row in conn.execute("PRAGMA table_info(payment_beasiswa)").fetchall()]
    conn.close()
    assert "tgl_Paid_LAND"   in cols, "Missing tgl_Paid_LAND in payment_beasiswa"
    assert "tgl_Paid_ENERGY" in cols, "Missing tgl_Paid_ENERGY in payment_beasiswa"
    assert "tgl_Paid_SETF"   in cols, "Missing tgl_Paid_SETF in payment_beasiswa"


def test_set_pam_complete_cascade_advance_pillar_sets_paid_not_complete():
    conn = get_conn()
    sid = _insert_siswa(conn)
    pam_id, pa_id = _insert_pam_beasiswa(conn, "etf_pa", "etf_pa_lines", "ETF", "ADVANCE", sid)
    conn.close()

    result = set_pam_complete_cascade(pam_id, "2026-07-10", COMPANY_ID)
    assert result["ok"] is True

    conn = get_conn()
    pam = conn.execute("SELECT status, pillar FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    pb  = conn.execute(
        "SELECT status FROM payment_beasiswa WHERE pam=?", ("PAM-ETF-06-2026-001",)
    ).fetchone()
    conn.close()

    assert pam["status"] == "complete"   # header flow unchanged
    assert pam["pillar"] == "ADVANCE"    # not yet moved — realization hasn't happened
    assert pb["status"]  == "paid"       # NOT 'complete' — quarantined until realize


# ── realize_advance_payment tests ────────────────────────────────────────────

from modules.payment_memo.service import save_pa_payment


def _setup_paid_advance(pam_no="PAM-030-ETF-07-2026", amount=3_000_000):
    """Helper: create + pay one Advance payment_beasiswa row. Returns (payment_id, pam_id)."""
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": pam_no, "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": amount}],
    })
    conn = get_conn()
    pam_id     = conn.execute(
        "SELECT id FROM pam_records WHERE company_id=? AND pam_no=?", (COMPANY_ID, pam_no)
    ).fetchone()["id"]
    payment_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE pam=?", (pam_no,)
    ).fetchone()["id"]
    conn.close()
    set_pam_complete_cascade(pam_id, "2026-07-10", COMPANY_ID)
    return payment_id, pam_id


def test_realize_advance_payment_updates_amount_and_closes_pillar():
    from modules.payment_memo.service import realize_advance_payment
    payment_id, pam_id = _setup_paid_advance()

    result = realize_advance_payment(payment_id, 2_700_000, "2026-07-20", COMPANY_ID)
    assert result["ok"] is True
    assert result["selisih"] == 300_000   # 3_000_000 advance - 2_700_000 realized

    conn = get_conn()
    pb  = conn.execute(
        "SELECT amount, realized_amount, tgl_realisasi, status FROM payment_beasiswa WHERE id=?",
        (payment_id,)
    ).fetchone()
    pam = conn.execute("SELECT pillar FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    conn.close()

    assert pb["amount"]          == 2_700_000
    assert pb["realized_amount"] == 2_700_000
    assert pb["tgl_realisasi"]   == "2026-07-20"
    assert pb["status"]          == "complete"
    assert pam["pillar"]         == "AGRI"   # moved out of ADVANCE


def test_realize_advance_payment_rejects_not_yet_paid():
    from modules.payment_memo.service import realize_advance_payment
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": "PAM-031-ETF-07-2026", "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_000_000}],
    })
    conn = get_conn()
    payment_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE pam=?", ("PAM-031-ETF-07-2026",)
    ).fetchone()["id"]
    conn.close()

    result = realize_advance_payment(payment_id, 900_000, "2026-07-20", COMPANY_ID)
    assert result["ok"] is False


def test_realize_advance_payment_rejects_non_advance_row():
    from modules.payment_memo.service import realize_advance_payment
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",   # route=gl
        "pam_no": "PAM-032-ETF-07-2026", "keterangan": "gl",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_000_000}],
    })
    conn = get_conn()
    payment_id = conn.execute(
        "SELECT id FROM payment_beasiswa WHERE pam=?", ("PAM-032-ETF-07-2026",)
    ).fetchone()["id"]
    conn.close()

    result = realize_advance_payment(payment_id, 900_000, "2026-07-20", COMPANY_ID)
    assert result["ok"] is False
