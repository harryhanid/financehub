# tests/test_pam_service.py
import os, sys, pytest, calendar
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from database import init_db, get_conn
from modules.payment_memo.service import (
    generate_pam_number, create_pam_record,
    get_pam_list, get_coa_list, update_pam_gl_account,
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
    no = generate_pam_number(COMPANY_ID, COMPANY_CODE, "2026", conn)
    conn.close()
    assert no == "PAM/ETF/2026/001"


def test_generate_pam_number_increments():
    conn = get_conn()
    no1 = generate_pam_number(COMPANY_ID, COMPANY_CODE, "2026", conn)
    conn.execute(
        """INSERT INTO pam_records (company_id, pam_no, pam_date, gl_account,
           cost_center, pt, requestors_name, keterangan, total_amount, due_date)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, no1, "2026-05-31", "70110230", "", "PT. SMART Tbk",
         "Jany Turkanda", "Harry, Joni", 5000000, "2026-06-30")
    )
    conn.commit()
    no2 = generate_pam_number(COMPANY_ID, COMPANY_CODE, "2026", conn)
    conn.close()
    assert no2 == "PAM/ETF/2026/002"


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
    assert row["pam_no"]          == "PAM/ETF/2026/001"
    assert row["gl_account"]      == "70110230"
    assert row["cost_center"]     == "1008C1POFF"   # SMART Tbk
    assert row["requestors_name"] == "Jany Turkanda"
    assert row["keterangan"]      == "Harry, Joni"
    assert row["total_amount"]    == 7500000.0
    assert row["due_date"]        == "2026-06-30"
    assert row["status"]          == "draft"


def test_create_pam_record_updates_payment_pam_field():
    conn = get_conn()
    # Insert a payment_beasiswa row first
    cur = conn.execute(
        """INSERT INTO payment_beasiswa
           (company_id, siswa_code, cat1, cat2, tanggal, amount, pillar, perusahaan, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (COMPANY_ID, "S001", "By Pendidikan", "Semester 1",
         "2026-05-31", 2000000, "AGRI", "PT. SMART Tbk", "draft")
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
    assert rows[0]["pam_no"] == "PAM/ETF/2026/001"


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
