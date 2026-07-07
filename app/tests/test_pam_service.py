# tests/test_pam_service.py
import os, sys, pytest, calendar
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.payment_memo.service import (
    generate_pam_number, create_pam_record,
    get_pam_list, get_coa_list, update_pam_gl_account,
    update_pam_status, update_pam_record, get_pam_payments,
)

COMPANY_ID   = 2   # ETF
COMPANY_CODE = "ETF"

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)


def test_generate_pam_number_first():
    conn = get_conn()
    no = generate_pam_number(COMPANY_ID, COMPANY_CODE, "2026", "05", conn)
    conn.close()
    assert no == "PAM-001-ETF-05-2026"


def test_generate_pam_number_increments():
    conn = get_conn()
    no1 = generate_pam_number(COMPANY_ID, COMPANY_CODE, "2026", "05", conn)
    conn.execute(
        """INSERT INTO pam_records (company_id, pam_no, pam_date, gl_account,
           cost_center, pt, requestors_name, keterangan, total_amount, due_date)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, no1, "2026-05-31", "70110230", "", "PT. SMART Tbk",
         "Jany Turkanda", "Harry, Joni", 5000000, "2026-06-30")
    )
    conn.commit()
    no2 = generate_pam_number(COMPANY_ID, COMPANY_CODE, "2026", "05", conn)
    conn.close()
    assert no2 == "PAM-002-ETF-05-2026"


def test_get_coa_list_returns_14():
    coa = get_coa_list()
    assert len(coa) == 14
    codes = [c["gl_code"] for c in coa]
    assert "70110230" in codes   # default
    assert "70107800" in codes   # Sponsorship


def test_create_pam_record_inserts_row():
    conn = get_conn()
    pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
        "pam_date":       "2026-05-31",
        "pt":             "PT. SMART Tbk",
        "keterangan":     "Harry, Joni",
        "total_amount":   7500000.0,
        "payment_ids":    [],
    })
    conn.commit()
    row = conn.execute(
        "SELECT * FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["pam_no"]          == "PAM-001-ETF-05-2026"
    assert row["gl_account"]      == "70110230"
    assert row["cost_center"]     == "1008C1POFF"   # SMART Tbk
    assert row["requestors_name"] == "Jany Turkanda"
    assert row["keterangan"]      == "Harry, Joni"
    assert row["total_amount"]    == 7500000.0
    assert row["due_date"]        == "2026-06-30"
    assert row["status"]          == "open"


def test_create_pam_record_updates_payment_pam_field():
    conn = get_conn()
    # Insert a payment_beasiswa row first
    cur = conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, perusahaan, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "By Pendidikan", "Semester 1",
         "2026-05-31", 2000000, "AGRI", "PT. SMART Tbk", "open")
    )
    payment_id = cur.lastrowid
    pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
        "pam_date":     "2026-05-31",
        "pt":           "PT. SMART Tbk",
        "keterangan":   "Harry",
        "total_amount": 2000000.0,
        "payment_ids":  [payment_id],
    })
    conn.commit()
    pb_row = conn.execute(
        "SELECT pam FROM payment_beasiswa WHERE id=?", (payment_id,)
    ).fetchone()
    conn.close()
    assert pb_row["pam"] == pam_no


def test_get_pam_list_empty():
    result = get_pam_list(COMPANY_ID)
    assert result == []


def test_get_pam_list_returns_inserted():
    conn = get_conn()
    create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
        "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
        "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
    })
    conn.commit()
    conn.close()
    rows = get_pam_list(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["pam_no"] == "PAM-001-ETF-05-2026"


def test_update_pam_gl_account_success():
    conn = get_conn()
    pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
        "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
        "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
    })
    conn.commit()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]
    conn.close()
    result = update_pam_gl_account(pam_id, "70107800", COMPANY_ID)
    assert result["ok"] is True
    conn2 = get_conn()
    row = conn2.execute("SELECT gl_account FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    conn2.close()
    assert row["gl_account"] == "70107800"


def test_update_pam_status_on_process():
    conn = get_conn()
    pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
        "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
        "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
    })
    conn.commit()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]
    conn.close()
    result = update_pam_status(pam_id, "on_process", COMPANY_ID)
    assert result["ok"] is True
    conn2 = get_conn()
    row = conn2.execute("SELECT status FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    conn2.close()
    assert row["status"] == "on_process"


def test_update_pam_status_invalid():
    conn = get_conn()
    pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
        "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
        "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
    })
    conn.commit()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]
    conn.close()
    result = update_pam_status(pam_id, "invalid_status", COMPANY_ID)
    assert result["ok"] is False


def test_update_pam_record_fields():
    conn = get_conn()
    pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
        "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
        "keterangan": "Lama", "total_amount": 1000000.0, "payment_ids": [],
    })
    conn.commit()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]
    conn.close()
    result = update_pam_record(pam_id, {
        "keterangan": "Baru", "requestors_name": "Sari", "total_amount": 2000000.0
    }, COMPANY_ID)
    assert result["ok"] is True
    conn2 = get_conn()
    row = conn2.execute("SELECT * FROM pam_records WHERE id=?", (pam_id,)).fetchone()
    conn2.close()
    assert row["keterangan"]      == "Baru"
    assert row["requestors_name"] == "Sari"
    assert row["total_amount"]    == 2000000.0


def test_update_pam_record_not_found():
    result = update_pam_record(9999, {"keterangan": "X"}, COMPANY_ID)
    assert result["ok"] is False


def test_update_pam_gl_account_invalid_code():
    conn = get_conn()
    pam_no = create_pam_record(conn, COMPANY_ID, COMPANY_CODE, {
        "pam_date": "2026-05-31", "pt": "PT. SMART Tbk",
        "keterangan": "Harry", "total_amount": 1000000.0, "payment_ids": [],
    })
    conn.commit()
    pam_id = conn.execute(
        "SELECT id FROM pam_records WHERE pam_no=?", (pam_no,)
    ).fetchone()["id"]
    conn.close()
    result = update_pam_gl_account(pam_id, "99999999", COMPANY_ID)
    assert result["ok"] is False


def _seed_siswa_and_payment(conn, company_id, pam_no):
    conn.execute(
        """INSERT INTO siswa (company_id, code, nama, bank, norek, namarek,
           jenjang, program, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (company_id, "S001", "Harry Santoso", "BCA", "1234567890",
         "Harry Santoso", "S1", "SMART", "Aktif")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount,
            pillar, perusahaan, pam, status)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (company_id, "S001", "General", "Sem 1", "2026-05-26",
         5000000, "ETF", "PT. SMART Tbk", pam_no, "open")
    )
    conn.commit()


def test_get_pam_payments_returns_students():
    conn = get_conn()
    _seed_siswa_and_payment(conn, COMPANY_ID, "PAM-052-ETF-05-2026")
    conn.close()
    rows = get_pam_payments("PAM-052-ETF-05-2026", COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["nama"] == "Harry Santoso"
    assert rows[0]["bank"] == "BCA"
    assert rows[0]["amount"] == 5000000


def test_get_pam_payments_empty_for_wrong_company():
    conn = get_conn()
    _seed_siswa_and_payment(conn, COMPANY_ID, "PAM-052-ETF-05-2026")
    conn.close()
    rows = get_pam_payments("PAM-052-ETF-05-2026", 999)
    assert rows == []


# ── Days of PAM ────────────────────────────────────────────────────────────────

def _seed_payment_with_pam(conn, company_id, siswa_code, pam_no):
    """Helper: insert one payment_beasiswa row that has a pam assigned."""
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar,
            pam, perusahaan, tgl_pengajuan, tgl_receive, tgl_pa, tgl_final)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, siswa_code, "Beasiswa", "Semester",
         "2026-05-01", 5000000.0, "AGRI",
         pam_no, "PT. SMART Tbk",
         "2026-05-02", "2026-05-05", "2026-05-10", "2026-05-15")
    )
    conn.commit()


def test_get_days_of_pam_returns_rows_with_pam():
    from modules.payment_memo.service import get_days_of_pam
    conn = get_conn()
    # seed siswa
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Budi Santoso")
    )
    _seed_payment_with_pam(conn, COMPANY_ID, "S001", "PAM-001-ETF-05-2026")
    # seed pam_records so the JOIN works (source=etf_agri for AGRI)
    conn.execute(
        "INSERT INTO pam_records (company_id, pam_no, source) VALUES (?,?,?)",
        (COMPANY_ID, "PAM-001-ETF-05-2026", "etf_agri")
    )
    # payment without pam should NOT appear
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, tanggal, amount) VALUES (?,?,?,?,?)",
        (COMPANY_ID, "S001", "Beasiswa", "2026-05-01", 1000000.0)
    )
    conn.commit()
    conn.close()

    result = get_days_of_pam(COMPANY_ID, paid_only=False)
    assert result["total"] == 1
    rows = result["rows"]
    assert len(rows) == 1
    r = rows[0]
    assert r["pam_no"]      == "PAM-001-ETF-05-2026"
    assert r["siswa_code"]  == "S001"
    assert r["nama"]        == "Budi Santoso"
    assert r["cat1"]        == "Beasiswa"
    assert r["perusahaan"]  == "PT. SMART Tbk"
    assert r["amount"]      == 5000000.0
    assert r["tgl_receive"] == "2026-05-05"


def test_get_days_of_pam_empty_pam_excluded():
    from modules.payment_memo.service import get_days_of_pam
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_beasiswa (company_id, siswa_code, cat1, tanggal, amount, pam) VALUES (?,?,?,?,?,?)",
        (COMPANY_ID, "S002", "Beasiswa", "2026-05-01", 1000000.0, "")
    )
    conn.commit()
    conn.close()
    result = get_days_of_pam(COMPANY_ID)
    assert result["rows"] == []
    assert result["total"] == 0


def test_get_days_of_pam_different_company_isolated():
    from modules.payment_memo.service import get_days_of_pam
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Budi")
    )
    _seed_payment_with_pam(conn, COMPANY_ID, "S001", "PAM-001-ETF-05-2026")
    conn.execute(
        "INSERT INTO pam_records (company_id, pam_no, source) VALUES (?,?,?)",
        (COMPANY_ID, "PAM-001-ETF-05-2026", "etf_agri")
    )
    conn.commit()
    conn.close()
    # Company 99 should see nothing
    result = get_days_of_pam(99)
    assert result["rows"] == []
    assert result["total"] == 0


# ── Bulk update dates ─────────────────────────────────────────────────────────

def test_bulk_update_dates_only_filled_fields():
    from modules.payment_memo.service import bulk_update_dates
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Budi")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, tanggal, amount, pam,
            tgl_pengajuan, tgl_receive, tgl_pa, tgl_final)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "Beasiswa", "2026-05-01", 5000000.0,
         "PAM-001-ETF-05-2026", None, None, None, None)
    )
    conn.commit()
    row_id = conn.execute("SELECT id FROM payment_beasiswa WHERE siswa_code='S001'").fetchone()["id"]
    conn.close()

    result = bulk_update_dates(
        ids=[row_id],
        dates={"tgl_receive": "2026-05-10", "tgl_final": ""},
        company_id=COMPANY_ID
    )
    assert result["ok"] is True
    assert result["updated"] == 1

    conn2 = get_conn()
    r = conn2.execute("SELECT * FROM payment_beasiswa WHERE id=?", (row_id,)).fetchone()
    conn2.close()
    assert r["tgl_receive"] == "2026-05-10"
    assert r["tgl_final"]   is None       # empty string → not updated


def test_bulk_update_dates_no_ids_returns_error():
    from modules.payment_memo.service import bulk_update_dates
    result = bulk_update_dates(ids=[], dates={"tgl_receive": "2026-05-10"}, company_id=COMPANY_ID)
    assert result["ok"] is False


def test_bulk_update_dates_no_dates_returns_error():
    from modules.payment_memo.service import bulk_update_dates
    result = bulk_update_dates(ids=[1], dates={}, company_id=COMPANY_ID)
    assert result["ok"] is False


def test_bulk_update_dates_wrong_company_not_updated():
    from modules.payment_memo.service import bulk_update_dates
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S001", "Budi")
    )
    conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, tanggal, amount, pam, tgl_receive)
           VALUES (?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "Beasiswa", "2026-05-01", 5000000.0,
         "PAM-001-ETF-05-2026", "2026-04-01")
    )
    conn.commit()
    row_id = conn.execute("SELECT id FROM payment_beasiswa WHERE siswa_code='S001'").fetchone()["id"]
    conn.close()

    # Try to update with wrong company_id=99
    result = bulk_update_dates(ids=[row_id], dates={"tgl_receive": "2026-05-10"}, company_id=99)
    assert result["updated"] == 0

    conn2 = get_conn()
    r = conn2.execute("SELECT tgl_receive FROM payment_beasiswa WHERE id=?", (row_id,)).fetchone()
    conn2.close()
    assert r["tgl_receive"] == "2026-04-01"   # unchanged


def test_insert_payment_rows_returns_ids_and_total():
    from modules.beasiswa.service import insert_payment_rows
    conn = get_conn()
    rows = [
        {"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
         "amount": 5_000_000},
        {"siswa_code": "S002", "cat1": "By Pendidikan", "cat2": "Semester 2",
         "amount": 3_000_000},
    ]
    result = insert_payment_rows(conn, COMPANY_ID, COMPANY_CODE,
                                  "2026-06-15", "ETF", "PT. ABC", rows)
    conn.commit()
    assert result["ok"] is True
    assert len(result["payment_ids"]) == 2
    assert result["total"] == 8_000_000
    count = conn.execute("SELECT COUNT(*) FROM pam_records").fetchone()[0]
    conn.close()
    assert count == 0


def test_save_pa_payment_creates_single_pam_record_with_correct_total():
    from modules.payment_memo.service import save_pa_payment
    rows = [
        {"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
         "amount": 5_000_000},
        {"siswa_code": "S002", "cat1": "By Pendidikan", "cat2": "Semester 2",
         "amount": 3_000_000},
    ]
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab":        "agri",
        "tanggal":    "2026-06-15",
        "pam_no":     "PAM-001-ETF-06-2026",
        "keterangan": "Test PAM",
        "perusahaan": "PT. ABC",
        "pillar":     "ETF",
        "rows":       rows,
    })
    assert result["ok"] is True
    conn = get_conn()
    records = conn.execute(
        "SELECT * FROM pam_records WHERE company_id=?", (COMPANY_ID,)
    ).fetchall()
    conn.close()
    assert len(records) == 1
    assert records[0]["pam_no"]       == "PAM-001-ETF-06-2026"
    assert records[0]["total_amount"] == 8_000_000


def test_get_next_pam_no_land_prefix():
    from modules.payment_memo.service import get_next_pam_no
    pam_no = get_next_pam_no(COMPANY_ID, COMPANY_CODE, "sml", "2026-06-15")
    assert pam_no == "PAM-001-LAND-06-2026"


def test_save_pa_payment_sets_pillar_on_pam_records():
    """Bug: pillar missing from pam_records INSERT → record not visible in pillar tab."""
    from modules.payment_memo.service import save_pa_payment
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab":        "app",
        "tanggal":    "2026-06-15",
        "pam_no":     "PAM-001-APP-06-2026",
        "keterangan": "Test pillar",
        "perusahaan": "PT. APP",
        "pillar":     "APP",
        "rows":       [{"siswa_code": "S001", "cat1": "By Pendidikan",
                        "cat2": "Semester 1", "amount": 2_000_000}],
    })
    assert result["ok"] is True, result.get("pesan")
    conn = get_conn()
    rec = conn.execute(
        "SELECT pillar FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-001-APP-06-2026")
    ).fetchone()
    conn.close()
    assert rec is not None
    assert rec["pillar"] == "APP", f"Expected 'APP', got {rec['pillar']!r}"


def test_save_pa_payment_sets_source_beasiswa():
    """Bug: source was 'etf_app' / 'etf_agri' — should be 'beasiswa' for iPay beasiswa flow."""
    from modules.payment_memo.service import save_pa_payment
    for tab, pillar in [("agri", "AGRI"), ("app", "APP"), ("sml", "LAND"), ("setf", "SETF")]:
        result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
            "tab":        tab,
            "tanggal":    "2026-06-15",
            "pam_no":     f"PAM-001-{pillar}-06-2026",
            "keterangan": f"Test {tab}",
            "perusahaan": "PT. Test",
            "pillar":     pillar,
            "rows":       [{"siswa_code": "S001", "cat1": "By Pendidikan",
                            "cat2": "Semester 1", "amount": 1_000_000}],
        })
        assert result["ok"] is True, f"tab={tab}: {result.get('pesan')}"
        conn = get_conn()
        rec = conn.execute(
            "SELECT source FROM pam_records WHERE company_id=? AND pam_no=?",
            (COMPANY_ID, f"PAM-001-{pillar}-06-2026")
        ).fetchone()
        conn.close()
        assert rec["source"] == "beasiswa", f"tab={tab}: expected 'beasiswa', got {rec['source']!r}"


def test_set_paid_cascades_to_payment_beasiswa():
    """Lifecycle: setting tanggal_bayar on a beasiswa PAM must complete payment_beasiswa too."""
    from modules.payment_memo.service import save_pa_payment, set_pam_complete_cascade
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab":        "app",
        "tanggal":    "2026-06-10",
        "pam_no":     "PAM-001-APP-06-2026",
        "keterangan": "cascade test",
        "perusahaan": "PT. X",
        "pillar":     "APP",
        "rows":       [{"siswa_code": "S001", "cat1": "By Pendidikan",
                        "cat2": "Semester 1", "amount": 5_000_000}],
    })
    assert result["ok"] is True
    conn = get_conn()
    pam = conn.execute(
        "SELECT id FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-001-APP-06-2026")
    ).fetchone()
    conn.close()
    pam_id = pam["id"]

    paid = set_pam_complete_cascade(pam_id, "2026-06-20", COMPANY_ID)
    assert paid["ok"] is True

    conn = get_conn()
    pb = conn.execute(
        "SELECT status FROM payment_beasiswa WHERE pam=? AND company_id=?",
        ("PAM-001-APP-06-2026", COMPANY_ID)
    ).fetchone()
    pr = conn.execute(
        "SELECT status, tanggal_bayar FROM pam_records WHERE id=?", (pam_id,)
    ).fetchone()
    conn.close()

    assert pr["status"] == "complete"
    assert pr["tanggal_bayar"] == "2026-06-20"
    assert pb is not None, "payment_beasiswa row not found"
    assert pb["status"] == "complete", f"Expected complete, got {pb['status']!r}"


def test_insert_payment_rows_advance_route_sets_advance_amount():
    from modules.beasiswa.service import insert_payment_rows
    conn = get_conn()
    rows = [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5_000_000}]
    result = insert_payment_rows(conn, COMPANY_ID, COMPANY_CODE, "2026-07-07", "AGRI", "PT. ABC",
                                  rows, route="advance")
    conn.commit()
    assert result["ok"] is True
    row = conn.execute(
        "SELECT advance_amount, realized_amount, pillar FROM payment_beasiswa WHERE id=?",
        (result["payment_ids"][0],)
    ).fetchone()
    conn.close()
    assert row["advance_amount"]  == 5_000_000
    assert row["realized_amount"] is None
    assert row["pillar"]          == "AGRI"   # target pillar unchanged, never "ADVANCE" here


def test_insert_payment_rows_default_route_gl_leaves_advance_amount_null():
    from modules.beasiswa.service import insert_payment_rows
    conn = get_conn()
    rows = [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5_000_000}]
    result = insert_payment_rows(conn, COMPANY_ID, COMPANY_CODE, "2026-07-07", "AGRI", "PT. ABC", rows)
    conn.commit()
    row = conn.execute(
        "SELECT advance_amount FROM payment_beasiswa WHERE id=?", (result["payment_ids"][0],)
    ).fetchone()
    conn.close()
    assert row["advance_amount"] is None


def test_save_pa_payment_route_advance_quarantines_pam_records():
    from modules.payment_memo.service import save_pa_payment
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab":        "agri",
        "route":      "advance",
        "tanggal":    "2026-07-07",
        "pam_no":     "PAM-001-ETF-07-2026",
        "keterangan": "Advance test",
        "perusahaan": "PT. ABC",
        "pillar":     "AGRI",
        "rows":       [{"siswa_code": "S001", "cat1": "By Pendidikan",
                        "cat2": "Semester 1", "amount": 2_000_000}],
    })
    assert result["ok"] is True
    conn = get_conn()
    pam = conn.execute(
        "SELECT pillar FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-001-ETF-07-2026")
    ).fetchone()
    pb = conn.execute(
        "SELECT pillar, advance_amount FROM payment_beasiswa WHERE pam=?",
        ("PAM-001-ETF-07-2026",)
    ).fetchone()
    conn.close()
    assert pam["pillar"] == "ADVANCE"
    assert pb["pillar"]  == "AGRI"          # target pillar preserved on the line
    assert pb["advance_amount"] == 2_000_000


def test_save_pa_payment_route_gl_default_unchanged():
    from modules.payment_memo.service import save_pa_payment
    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab":        "agri",
        "tanggal":    "2026-07-07",
        "pam_no":     "PAM-002-ETF-07-2026",
        "keterangan": "GL test",
        "perusahaan": "PT. ABC",
        "pillar":     "AGRI",
        "rows":       [{"siswa_code": "S001", "cat1": "By Pendidikan",
                        "cat2": "Semester 1", "amount": 1_000_000}],
    })
    assert result["ok"] is True
    conn = get_conn()
    pam = conn.execute(
        "SELECT pillar FROM pam_records WHERE company_id=? AND pam_no=?",
        (COMPANY_ID, "PAM-002-ETF-07-2026")
    ).fetchone()
    conn.close()
    assert pam["pillar"] == "AGRI"


def test_save_pa_payment_advance_tags_pa_lines_route():
    from modules.payment_memo.service import save_pa_payment
    conn = get_conn()
    conn.execute(
        "INSERT INTO siswa (company_id, code, nama) VALUES (?,?,?)",
        (COMPANY_ID, "S010", "Test Siswa")
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa (company_id, pa_number, status, created_at) VALUES (?,?,?,?)",
        (COMPANY_ID, "PA/TEST/001/2026", "on_process", "2026-07-07T00:00:00")
    )
    pa_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO etf_pa_lines (pa_id, student_id, jenis_pembayaran, jumlah_pembayaran) VALUES (?,?,?,?)",
        (pa_id, sid, "By Pendidikan", 3_000_000)
    )
    line_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    result = save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": "PAM-003-ETF-07-2026", "keterangan": "x",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S010", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 3_000_000, "etf_pa_line_id": line_id}],
    })
    assert result["ok"] is True

    conn = get_conn()
    line = conn.execute("SELECT route FROM etf_pa_lines WHERE id=?", (line_id,)).fetchone()
    conn.close()
    assert line["route"] == "advance"


def test_get_advance_payments_returns_quarantined_lines_only():
    from modules.payment_memo.service import save_pa_payment, get_advance_payments
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": "PAM-020-ETF-07-2026", "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 2_500_000}],
    })
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "tanggal": "2026-07-07",   # route=gl (default) — must NOT show up
        "pam_no": "PAM-021-ETF-07-2026", "keterangan": "gl",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_000_000}],
    })
    rows = get_advance_payments(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["pam"]    == "PAM-020-ETF-07-2026"
    assert rows[0]["amount"] == 2_500_000


def test_get_advance_payments_filters_by_status():
    from modules.payment_memo.service import save_pa_payment, get_advance_payments
    save_pa_payment(COMPANY_ID, COMPANY_CODE, {
        "tab": "agri", "route": "advance", "tanggal": "2026-07-07",
        "pam_no": "PAM-022-ETF-07-2026", "keterangan": "adv",
        "perusahaan": "PT. ABC", "pillar": "AGRI",
        "rows": [{"siswa_code": "S001", "cat1": "By Pendidikan", "cat2": "Semester 1",
                  "amount": 1_500_000}],
    })
    assert get_advance_payments(COMPANY_ID, status="open") != []
    assert get_advance_payments(COMPANY_ID, status="paid") == []
