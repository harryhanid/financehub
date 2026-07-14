import os, sys, pytest, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_sahabat_etf.db")

from database import init_db, get_conn
from modules.beasiswa.service import add_siswa, add_budget_batch, add_payment_batch
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars,
)

COMPANY_ID = 2  # ETF


@pytest.fixture(autouse=True)
def clean_db():
    import time
    # Clean and recreate tables for each test
    # (Simpler than trying to fight Windows SQLite file locks with WAL mode)
    if os.path.exists(config.DB_PATH):
        try:
            conn = sqlite3.connect(config.DB_PATH)
            # Drop all data-bearing tables except schema tables
            for table in ['siswa', 'budget_beasiswa', 'payment_beasiswa', 'payment_memo']:
                try:
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
                except Exception:
                    pass
            conn.commit()
            conn.close()
        except Exception:
            pass
    # Recreate tables
    init_db()
    yield
    # No post-test cleanup needed - next test's setup will truncate


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
    # Type contract: all 4 financial fields must always be float
    assert isinstance(rows[0]["budget_total"], float)
    assert isinstance(rows[0]["payment_total"], float)
    assert isinstance(rows[0]["realisasi_total"], float)
    assert isinstance(rows[0]["sisa_budget"], float)


def test_get_kategori_breakdown_groups_by_cat1():
    _add_siswa("9990010", "Siswa Kategori")
    add_budget_batch(COMPANY_ID, "9990010", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000},
         {"cat1": "By Tunjangan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990010", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 3000000}])
    _mark_complete("9990010")

    result = get_kategori_breakdown(COMPANY_ID)
    by_cat = {k["cat1"]: k for k in result["kategori"]}
    assert by_cat["By Pendidikan"]["budget"] == 5000000
    assert by_cat["By Pendidikan"]["realisasi"] == 3000000
    assert by_cat["By Tunjangan"]["budget"] == 1000000
    assert by_cat["By Tunjangan"]["payment"] == 0
    assert result["over_budget"] == []


def test_get_kategori_breakdown_flags_over_budget_siswa():
    _add_siswa("9990011", "Siswa Over Budget")
    add_budget_batch(COMPANY_ID, "9990011", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990011", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    _mark_complete("9990011")

    result = get_kategori_breakdown(COMPANY_ID)
    assert len(result["over_budget"]) == 1
    o = result["over_budget"][0]
    assert o["nama"] == "Siswa Over Budget"
    assert o["selisih"] == 1000000


def test_get_siswa_detail_returns_tagged_rows_sorted_by_date():
    _add_siswa("9990020", "Siswa Detail")
    add_budget_batch(COMPANY_ID, "9990020", "2026-02-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 2", "amount": 4000000}])
    add_payment_batch(COMPANY_ID, "9990020", "2026-01-01", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])

    rows = get_siswa_detail(COMPANY_ID, "9990020")
    assert len(rows) == 2
    assert rows[0]["tanggal"] == "2026-01-01"
    assert rows[0]["sumber"] == "Payment"
    assert rows[1]["tanggal"] == "2026-02-01"
    assert rows[1]["sumber"] == "Budget"


def test_get_siswa_detail_isolated_by_siswa_code():
    _add_siswa("9990021", "Siswa A")
    _add_siswa("9990022", "Siswa B")
    add_budget_batch(COMPANY_ID, "9990021", "2026-01-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_budget_batch(COMPANY_ID, "9990022", "2026-01-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])

    rows = get_siswa_detail(COMPANY_ID, "9990021")
    assert len(rows) == 1
    assert rows[0]["amount"] == 1000000


def test_get_all_transactions_includes_all_sahabat_etf_siswa():
    _add_siswa("9990030", "Siswa A")
    _add_siswa("9990031", "Siswa B")
    _add_siswa("9990032", "Siswa Lain Program", program="SMART")
    add_budget_batch(COMPANY_ID, "9990030", "2026-01-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990031", "2026-01-02", "SETF", "ETF",
        [{"cat1": "By Tunjangan", "cat2": "Semester 1", "amount": 500000}])
    add_budget_batch(COMPANY_ID, "9990032", "2026-01-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 9999999}])

    rows = get_all_transactions(COMPANY_ID)
    assert len(rows) == 2
    codes = {r["siswa_code"] for r in rows}
    assert codes == {"9990030", "9990031"}


def test_get_available_years_returns_sorted_distinct_years():
    _add_siswa("9990040", "Siswa Tahun")
    add_budget_batch(COMPANY_ID, "9990040", "2025-03-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990040", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])

    years = get_available_years(COMPANY_ID)
    assert years == [2025, 2026]


def test_get_available_years_excludes_other_program():
    _add_siswa("9990041", "Siswa Lain", program="SMART")
    add_budget_batch(COMPANY_ID, "9990041", "2019-01-01", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    years = get_available_years(COMPANY_ID)
    assert years == []


def test_get_available_pillars_returns_sorted_distinct_pillars():
    _add_siswa("9990050", "Siswa Pillar")
    add_payment_batch(COMPANY_ID, "9990050", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])
    add_payment_batch(COMPANY_ID, "9990050", "2026-02-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])

    pillars = get_available_pillars(COMPANY_ID)
    assert pillars == ["APP", "SETF"]


def test_get_available_pillars_excludes_other_program():
    _add_siswa("9990051", "Siswa Pillar Lain Program", program="SMART")
    add_payment_batch(COMPANY_ID, "9990051", "2026-01-15", "AGRI", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])
    pillars = get_available_pillars(COMPANY_ID)
    assert pillars == []
