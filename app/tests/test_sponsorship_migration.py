import datetime
import openpyxl
import pytest
from modules.sponsorship.migrate import migrate_sponsorship_from_excel
from modules.sponsorship.service import list_perusahaan, list_transaksi, count_transaksi


@pytest.fixture
def fixture_perusahaan_xlsx(tmp_path):
    path = tmp_path / "cat1-3.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Cat1", "Cat2", "Cat3"])
    ws.append(["SMART", "AGRI", "AGRI"])
    ws.append(["IKPP", "APP", "APP"])
    wb.save(path)
    return str(path)


@pytest.fixture
def fixture_transaksi_xlsx(tmp_path):
    path = tmp_path / "database awal.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "Cat", "Description", "Year", "Tanggal Form Sponsor", "Tanggal Payment",
        "Cat1", "Lembaga/Perorangan", "Perihal", "Amount Request", "Reff", "Status",
        "Cat4", "Cat2", "Cat3", "APP", "AGRI", "ENERGY & FINANCE", "PROPERTY",
        "COA", "CC Total", "CC", "Source",
    ])
    ws.append([
        "Sponsorship", "Keagamaan", 2025, datetime.datetime(2025, 1, 6), datetime.datetime(2025, 3, 27),
        "SMART", "Klenteng Kong Miao TMII", "Minyak Goreng", 2520000, "-", "Done",
        "Exclude", "AGRI", "AGRI", 0, 2520000, 0, 0,
        "701078002", "SMT - Corporate Communication", "POSPON", "Sponsor",
    ])
    ws.append([
        "CSR Gedung", "Sosial", 2026, datetime.datetime(2026, 2, 1), None,
        "IKPP", "Yayasan Sosial", "Bantuan sosial", 1000000, "-", None,
        "Include", "APP", "APP", 1000000, 0, 0, 0,
        "701078002", "SMT - Corporate Communication", "POSPON", "Sponsor",
    ])
    ws.append(["   ", None, None, None, None, None, None, None, None, None, None,
               None, None, None, None, None, None, None, None, None, None, None])
    ws.append([
        "Sponsorship", "Media", 2026, datetime.datetime(2026, 3, 1), None,
        "TAPIAN", "Media Partner", "Iklan", 500000, "Shingo Kobayashi", None,
        None, "AGRI", "AGRI", 0, 500000, 0, 0,
        "701078002", "SMT - Corporate Communication", "POSPON", "Sponsor",
    ])
    wb.save(path)
    return str(path)


def test_migrate_imports_perusahaan_and_transaksi(app, fixture_perusahaan_xlsx, fixture_transaksi_xlsx):
    result = migrate_sponsorship_from_excel(fixture_perusahaan_xlsx, fixture_transaksi_xlsx)
    assert result["perusahaan"] == 2
    assert result["transaksi"] == 3  # 4 data rows minus 1 skipped '   ' row
    assert len(result["skipped"]) == 1
    assert list_perusahaan() == [
        {"cat1": "IKPP", "cat2": "APP", "cat3": "APP"},
        {"cat1": "SMART", "cat2": "AGRI", "cat3": "AGRI"},
    ]


def test_migrate_imports_row_with_cat1_not_in_lookup(app, fixture_perusahaan_xlsx, fixture_transaksi_xlsx):
    migrate_sponsorship_from_excel(fixture_perusahaan_xlsx, fixture_transaksi_xlsx)
    rows = list_transaksi(1)
    tapian_rows = [r for r in rows if r["cat1"] == "TAPIAN"]
    assert len(tapian_rows) == 1
    assert tapian_rows[0]["cat2"] == "AGRI"
    assert tapian_rows[0]["cat3"] == "AGRI"


def test_migrate_preserves_dates_amounts_and_defaults(app, fixture_perusahaan_xlsx, fixture_transaksi_xlsx):
    migrate_sponsorship_from_excel(fixture_perusahaan_xlsx, fixture_transaksi_xlsx)
    rows = list_transaksi(1)
    row = next(r for r in rows if r["lembaga_perorangan"] == "Klenteng Kong Miao TMII")
    assert row["tanggal_form_sponsor"] == "2025-01-06"
    assert row["tanggal_payment"] == "2025-03-27"
    assert row["amount_request"] == 2520000
    assert row["coa"] == "701078002"
    assert row["cc_total"] == "SMT - Corporate Communication"


def test_migrate_handles_null_tanggal_payment_and_status(app, fixture_perusahaan_xlsx, fixture_transaksi_xlsx):
    migrate_sponsorship_from_excel(fixture_perusahaan_xlsx, fixture_transaksi_xlsx)
    rows = list_transaksi(1)
    row = next(r for r in rows if r["lembaga_perorangan"] == "Yayasan Sosial")
    assert row["tanggal_payment"] is None
    assert row["status"] is None


def test_migrate_is_idempotent_for_perusahaan(app, fixture_perusahaan_xlsx, fixture_transaksi_xlsx):
    migrate_sponsorship_from_excel(fixture_perusahaan_xlsx, fixture_transaksi_xlsx)
    result = migrate_sponsorship_from_excel(fixture_perusahaan_xlsx, fixture_transaksi_xlsx)
    assert result["perusahaan"] == 0  # INSERT OR IGNORE, already seeded
    assert count_transaksi(1) == 6  # re-running re-imports transaksi rows (by design — see Step 3 note)


def test_migrate_converts_reff_dash_to_none_and_passes_through_values(app, fixture_perusahaan_xlsx, fixture_transaksi_xlsx):
    migrate_sponsorship_from_excel(fixture_perusahaan_xlsx, fixture_transaksi_xlsx)
    rows = list_transaksi(1)
    # Row with Reff="-" should convert to None
    klenteng_row = next(r for r in rows if r["lembaga_perorangan"] == "Klenteng Kong Miao TMII")
    assert klenteng_row["reff"] is None
    # Row with Reff="Shingo Kobayashi" should pass through unchanged
    media_row = next(r for r in rows if r["lembaga_perorangan"] == "Media Partner")
    assert media_row["reff"] == "Shingo Kobayashi"
