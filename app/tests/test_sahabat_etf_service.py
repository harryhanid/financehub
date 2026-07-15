import os, sys, pytest, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_sahabat_etf.db")

from database import init_db, get_conn
from modules.beasiswa.service import add_siswa, add_budget_batch, add_payment_batch
from modules.sahabat_etf.service import (
    get_siswa_summary, get_kategori_breakdown, get_siswa_detail, get_all_transactions,
    get_available_years, get_available_pillars, get_monthly_breakdown,
    get_pillar_breakdown, get_yearly_breakdown, get_family_summary,
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


def test_get_siswa_summary_filters_by_year():
    _add_siswa("9990060", "Siswa Multi Tahun")
    add_budget_batch(COMPANY_ID, "9990060", "2025-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    add_budget_batch(COMPANY_ID, "9990060", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 3000000}])
    add_payment_batch(COMPANY_ID, "9990060", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    _mark_complete("9990060")

    rows = get_siswa_summary(COMPANY_ID, years=[2026])
    assert len(rows) == 1
    assert rows[0]["budget_total"] == 3000000
    assert rows[0]["realisasi_total"] == 1000000


def test_get_siswa_summary_filters_by_pillar():
    _add_siswa("9990061", "Siswa Pillar Filter")
    add_payment_batch(COMPANY_ID, "9990061", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990061", "2026-01-20", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    _mark_complete("9990061")

    rows = get_siswa_summary(COMPANY_ID, pillars=["SETF"])
    assert rows[0]["realisasi_total"] == 2000000


def test_get_siswa_summary_pillar_does_not_affect_budget():
    _add_siswa("9990063", "Siswa Budget Tak Terpengaruh Pillar")
    add_budget_batch(COMPANY_ID, "9990063", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000}])
    add_payment_batch(COMPANY_ID, "9990063", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    _mark_complete("9990063")

    rows = get_siswa_summary(COMPANY_ID, pillars=["SETF"])
    # budget tetap 5jt (tidak ikut difilter pillar) walau tidak ada payment SETF sama sekali
    assert rows[0]["budget_total"] == 5000000
    assert rows[0]["realisasi_total"] == 0


def test_get_siswa_summary_without_filters_unchanged():
    _add_siswa("9990062", "Siswa Default")
    add_budget_batch(COMPANY_ID, "9990062", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000}])
    rows = get_siswa_summary(COMPANY_ID)
    assert rows[0]["budget_total"] == 5000000


def test_get_kategori_breakdown_filters_by_year():
    _add_siswa("9990070", "Siswa Kategori Tahun")
    add_budget_batch(COMPANY_ID, "9990070", "2025-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_budget_batch(COMPANY_ID, "9990070", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])

    result = get_kategori_breakdown(COMPANY_ID, years=[2026])
    by_cat = {k["cat1"]: k for k in result["kategori"]}
    assert by_cat["By Pendidikan"]["budget"] == 2000000


def test_get_kategori_breakdown_filters_by_pillar():
    _add_siswa("9990071", "Siswa Kategori Pillar")
    add_payment_batch(COMPANY_ID, "9990071", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990071", "2026-01-20", "SETF", "ETF",
        [{"cat1": "By Tunjangan", "cat2": "Semester 1", "amount": 500000}])
    _mark_complete("9990071")

    result = get_kategori_breakdown(COMPANY_ID, pillars=["SETF"])
    by_cat = {k["cat1"]: k for k in result["kategori"]}
    assert "By Tunjangan" in by_cat
    assert "By Pendidikan" not in by_cat


def test_get_kategori_breakdown_over_budget_respects_filters():
    _add_siswa("9990072", "Siswa Over Filtered")
    add_budget_batch(COMPANY_ID, "9990072", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990072", "2025-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000}])
    _mark_complete("9990072")

    # Tanpa filter: realisasi (5jt, tahun 2025) > budget (1jt, tahun 2026) -> over budget
    result_all = get_kategori_breakdown(COMPANY_ID)
    assert len(result_all["over_budget"]) == 1

    # Filter tahun 2026 saja: realisasi 2025 tidak ikut terhitung -> tidak over budget
    result_2026 = get_kategori_breakdown(COMPANY_ID, years=[2026])
    assert result_2026["over_budget"] == []


def test_get_all_transactions_filters_by_year_and_pillar():
    _add_siswa("9990080", "Siswa Export Filter")
    add_budget_batch(COMPANY_ID, "9990080", "2025-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_budget_batch(COMPANY_ID, "9990080", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    add_payment_batch(COMPANY_ID, "9990080", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])
    add_payment_batch(COMPANY_ID, "9990080", "2026-01-20", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 700000}])

    rows = get_all_transactions(COMPANY_ID, years=[2026], pillars=["SETF"])
    assert len(rows) == 2  # 1 budget baris 2026 (pillar tidak memfilter budget) + 1 payment pillar SETF 2026
    sumbers = {(r["sumber"], r["amount"]) for r in rows}
    assert ("Budget", 2000000) in sumbers
    assert ("Payment", 700000) in sumbers


def test_get_monthly_breakdown_zero_fills_all_12_months():
    _add_siswa("9990090", "Siswa Bulanan")
    add_budget_batch(COMPANY_ID, "9990090", "2026-03-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])

    result = get_monthly_breakdown(COMPANY_ID, years=[2026])
    assert len(result["months"]) == 12
    assert result["months"][2]["bulan"] == 3
    assert result["months"][2]["budget"] == 1000000
    assert result["months"][0]["budget"] == 0.0  # Januari, tidak ada data


def test_get_monthly_breakdown_uses_latest_year_for_chart():
    _add_siswa("9990091", "Siswa Multi Tahun Bulanan")
    add_budget_batch(COMPANY_ID, "9990091", "2025-05-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 9999999}])
    add_budget_batch(COMPANY_ID, "9990091", "2026-05-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1500000}])

    result = get_monthly_breakdown(COMPANY_ID, years=[2025, 2026])
    assert result["chart_year"] == 2026
    assert result["months"][4]["budget"] == 1500000  # Mei tahun 2026, bukan 2025


def test_get_monthly_breakdown_comparison_covers_all_selected_years():
    _add_siswa("9990092", "Siswa Banding Tahun")
    add_payment_batch(COMPANY_ID, "9990092", "2025-06-10", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 700000}])
    add_payment_batch(COMPANY_ID, "9990092", "2026-06-10", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 900000}])
    _mark_complete("9990092")

    result = get_monthly_breakdown(COMPANY_ID, years=[2025, 2026])
    juni = result["comparison"][5]
    assert juni["bulan"] == 6
    assert juni["per_tahun"]["2025"] == 700000
    assert juni["per_tahun"]["2026"] == 900000


def test_get_monthly_breakdown_filters_by_pillar():
    _add_siswa("9990093", "Siswa Bulanan Pillar")
    add_payment_batch(COMPANY_ID, "9990093", "2026-07-10", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 400000}])
    add_payment_batch(COMPANY_ID, "9990093", "2026-07-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 600000}])
    _mark_complete("9990093")

    result = get_monthly_breakdown(COMPANY_ID, years=[2026], pillars=["SETF"])
    juli = result["months"][6]
    assert juli["realisasi"] == 600000


def test_get_monthly_breakdown_empty_years_returns_empty_structure():
    result = get_monthly_breakdown(COMPANY_ID, years=[])
    assert result == {"chart_year": None, "months": [], "comparison": []}


def test_get_siswa_summary_filters_by_multiple_pillars():
    _add_siswa("9990110", "Siswa Multi Pillar")
    add_payment_batch(COMPANY_ID, "9990110", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990110", "2026-01-20", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    add_payment_batch(COMPANY_ID, "9990110", "2026-01-25", "FINANCE", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 4000000}])
    _mark_complete("9990110")

    rows = get_siswa_summary(COMPANY_ID, pillars=["APP", "SETF"])
    assert rows[0]["realisasi_total"] == 3000000  # APP + SETF, tanpa FINANCE


def test_get_pillar_breakdown_groups_by_pillar():
    _add_siswa("9990130", "Siswa Pillar Breakdown")
    add_budget_batch(COMPANY_ID, "9990130", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 5000000}])
    add_budget_batch(COMPANY_ID, "9990130", "2026-01-10", "APP",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990130", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    _mark_complete("9990130")

    result = get_pillar_breakdown(COMPANY_ID)
    by_pillar = {p["pillar"]: p for p in result}
    assert by_pillar["SETF"]["budget"] == 5000000
    assert by_pillar["SETF"]["realisasi"] == 2000000
    assert by_pillar["SETF"]["sisa"] == 3000000
    assert by_pillar["APP"]["budget"] == 1000000
    assert by_pillar["APP"]["realisasi"] == 0


def test_get_pillar_breakdown_filters_by_year_not_by_pillar_arg():
    _add_siswa("9990131", "Siswa Pillar Tahun")
    add_budget_batch(COMPANY_ID, "9990131", "2025-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_budget_batch(COMPANY_ID, "9990131", "2026-01-10", "SETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])

    result = get_pillar_breakdown(COMPANY_ID, years=[2026])
    by_pillar = {p["pillar"]: p for p in result}
    assert by_pillar["SETF"]["budget"] == 2000000


def test_get_yearly_breakdown_groups_realisasi_by_year():
    _add_siswa("9990140", "Siswa Tahunan")
    add_payment_batch(COMPANY_ID, "9990140", "2025-06-10", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 700000}])
    add_payment_batch(COMPANY_ID, "9990140", "2026-06-10", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 900000}])
    _mark_complete("9990140")

    result = get_yearly_breakdown(COMPANY_ID)
    by_year = {y["tahun"]: y["realisasi"] for y in result}
    assert by_year == {2025: 700000, 2026: 900000}


def test_get_yearly_breakdown_filters_by_pillar():
    _add_siswa("9990141", "Siswa Tahunan Pillar")
    add_payment_batch(COMPANY_ID, "9990141", "2026-01-10", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 400000}])
    add_payment_batch(COMPANY_ID, "9990141", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 600000}])
    _mark_complete("9990141")

    result = get_yearly_breakdown(COMPANY_ID, pillars=["SETF"])
    assert result == [{"tahun": 2026, "realisasi": 600000}]


def test_get_yearly_breakdown_excludes_incomplete_payments():
    _add_siswa("9990142", "Siswa Tahunan Open")
    add_payment_batch(COMPANY_ID, "9990142", "2026-01-10", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])
    # status default 'open' — tidak di-mark complete

    result = get_yearly_breakdown(COMPANY_ID)
    assert result == []


def test_get_family_summary_groups_by_family_groups():
    _add_siswa("5260002", "Effendi Widjaja")
    _add_siswa("1240700", "Cathabell Virginia Fernanda Widjaja")
    add_payment_batch(COMPANY_ID, "5260002", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "1240700", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    _mark_complete("5260002")
    _mark_complete("1240700")

    families = get_family_summary(COMPANY_ID)
    assert len(families) == 1
    fam1 = families[0]
    assert fam1["family_key"] == "fam1"
    names = [m["nama"] for m in fam1["members"]]
    assert names == ["Effendi Widjaja", "Cathabell Virginia Fernanda Widjaja"]
    assert fam1["total_realisasi"] == 3000000


def test_get_family_summary_merges_duplicate_nama_in_same_group():
    # fam1 = 5260002, 1240700, 4220003 — 1240700 & 4220003 are the same person (Cathabell), 2 siswa records
    _add_siswa("5260002", "Effendi Widjaja")
    _add_siswa("1240700", "Cathabell Virginia Fernanda Widjaja")
    _add_siswa("4220003", "Cathabell Virginia Fernanda Widjaja")
    add_payment_batch(COMPANY_ID, "1240700", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1500000}])
    add_payment_batch(COMPANY_ID, "4220003", "2022-06-01", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 500000}])
    _mark_complete("1240700")
    _mark_complete("4220003")

    fam1 = get_family_summary(COMPANY_ID)[0]
    # 2 kode Cathabell tergabung jadi 1 member, bukan 2
    cathabell_members = [m for m in fam1["members"] if m["nama"] == "Cathabell Virginia Fernanda Widjaja"]
    assert len(cathabell_members) == 1
    assert cathabell_members[0]["realisasi"] == 2000000


def test_get_family_summary_label_numbering_for_repeated_marga():
    _add_siswa("5260002", "Effendi Widjaja")       # fam1 -> Widjaja
    _add_siswa("1240706", "Jety Widjaja")          # fam2 -> Widjaja
    _add_siswa("5260001", "Claudia Samaoen")       # fam5 -> Samaoen (unique marga)

    families = get_family_summary(COMPANY_ID)
    by_key = {f["family_key"]: f["label"] for f in families}
    assert by_key["fam1"] == "Keluarga Widjaja 1"
    assert by_key["fam2"] == "Keluarga Widjaja 2"
    assert by_key["fam5"] == "Keluarga Samaoen"  # marga unik -> tanpa angka


def test_get_family_summary_fallback_for_unmapped_siswa():
    _add_siswa("9999999", "Orang Baru Tanpa Grup")
    families = get_family_summary(COMPANY_ID)
    assert len(families) == 1
    fam = families[0]
    assert fam["family_key"] == "9999999"
    assert fam["label"] == "Keluarga Grup"
    assert fam["members"][0]["nama"] == "Orang Baru Tanpa Grup"


def test_get_family_summary_total_equals_sum_of_members():
    _add_siswa("1260001", "Budi Widjaja")
    _add_siswa("5250001", "Birgitta Jennifer Widjaja")
    add_payment_batch(COMPANY_ID, "1260001", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 700000}])
    add_payment_batch(COMPANY_ID, "5250001", "2026-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 300000}])
    _mark_complete("1260001")
    _mark_complete("5250001")

    fam3 = get_family_summary(COMPANY_ID)[0]
    assert fam3["total_realisasi"] == sum(m["realisasi"] for m in fam3["members"])
    assert fam3["total_realisasi"] == 1000000


def test_get_family_summary_respects_year_and_pillar_filters():
    _add_siswa("5260001", "Claudia Samaoen")
    add_payment_batch(COMPANY_ID, "5260001", "2025-01-15", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "5260001", "2026-01-15", "APP", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 2000000}])
    add_payment_batch(COMPANY_ID, "5260001", "2026-01-20", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 4000000}])
    _mark_complete("5260001")

    families = get_family_summary(COMPANY_ID, years=[2026], pillars=["SETF"])
    assert families[0]["total_realisasi"] == 4000000


def test_get_family_summary_empty_when_no_siswa():
    assert get_family_summary(COMPANY_ID) == []


def test_get_latest_payments_filters_by_kategori():
    _add_siswa("9990120", "Siswa Latest Kategori")
    add_payment_batch(COMPANY_ID, "9990120", "2026-01-10", "SETF", "ETF",
        [{"cat1": "By Pendidikan", "cat2": "Semester 1", "amount": 1000000}])
    add_payment_batch(COMPANY_ID, "9990120", "2026-01-11", "SETF", "ETF",
        [{"cat1": "By Tunjangan", "cat2": "Semester 1", "amount": 2000000}])
    _mark_complete("9990120")

    from modules.sahabat_etf.service import get_latest_payments
    rows = get_latest_payments(COMPANY_ID, kategori="By Tunjangan")
    assert len(rows) == 1
    assert rows[0]["amount"] == 2000000
