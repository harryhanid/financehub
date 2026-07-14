import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_sahabat_etf.db")

from database import init_db, get_conn
from modules.beasiswa.service import add_siswa, add_budget_batch, add_payment_batch
from modules.sahabat_etf.service import get_siswa_summary

COMPANY_ID = 2  # ETF


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_db()
    yield
    # Close any remaining connections before cleanup
    import sqlite3
    # Disable WAL mode to ensure file cleanup
    try:
        conn = sqlite3.connect(config.DB_PATH)
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.close()
    except:
        pass
    # Remove DB and WAL files
    import time
    time.sleep(0.1)  # Brief delay for file lock release
    for ext in ['', '-wal', '-shm']:
        path = config.DB_PATH + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass


def _add_siswa(code, nama, program="Sahabat ETF", company_id=COMPANY_ID):
    add_siswa(company_id, {
        "code": code, "nama": nama, "jenjang": "S1", "angkatan": 2024,
        "program": program, "fakultas": "", "universitas": "", "bank": "",
        "norek": "", "namarek": "", "referensi": "", "status": "Aktif", "catatan": "",
    })


def _mark_complete(siswa_code):
    conn = get_conn()
    conn.execute("UPDATE payment_beasiswa SET status='complete' WHERE siswa_code=?", (siswa_code,))
    conn.commit()
    conn.close()


def test_get_siswa_summary_aggregates_budget_payment_realisasi():
    _add_siswa("9990001", "Test Siswa")
    add_budget_batch(COMPANY_ID, "9990001", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000}])
    add_payment_batch(COMPANY_ID, "9990001", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 3000000}])
    _mark_complete("9990001")

    rows = get_siswa_summary(COMPANY_ID)
    assert len(rows) == 1
    r = rows[0]
    assert r["nama"] == "Test Siswa"
    assert r["budget_total"] == 5000000
    assert r["payment_total"] == 3000000
    assert r["realisasi_total"] == 3000000
    assert r["sisa_budget"] == 2000000


def test_get_siswa_summary_open_payment_not_counted_as_realisasi():
    _add_siswa("9990002", "Siswa Open")
    add_budget_batch(COMPANY_ID, "9990002", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990002", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    # status default 'open' — tidak di-mark complete

    r = get_siswa_summary(COMPANY_ID)[0]
    assert r["payment_total"] == 1000000
    assert r["realisasi_total"] == 0
    assert r["sisa_budget"] == 1000000


def test_get_siswa_summary_excludes_other_program():
    _add_siswa("9990003", "Siswa Lain", program="SMART")
    rows = get_siswa_summary(COMPANY_ID)
    assert rows == []


def test_get_siswa_summary_isolated_by_company():
    _add_siswa("9990004", "Siswa SMT", company_id=1)
    rows = get_siswa_summary(COMPANY_ID)  # query company 2 (ETF)
    assert rows == []


def test_get_siswa_summary_includes_siswa_with_no_transactions():
    _add_siswa("9990005", "Siswa Kosong")
    rows = get_siswa_summary(COMPANY_ID)
    assert len(rows) == 1
    assert rows[0]["budget_total"] == 0
    assert rows[0]["payment_total"] == 0
    assert rows[0]["realisasi_total"] == 0
    assert rows[0]["sisa_budget"] == 0
