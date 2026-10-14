# tests/test_mrc_category_map.py
import pytest

from modules.management_report import category_map as cm
from modules.management_report.coa_map import CoaParseError

HEADER = [None, "COA SMT", "Description", "COA ETF", "Description", "FROM :", "COA HO",
          "Sub Account", "CATEGORIES", "CATEGORIES 2", None, "BUDGET CATEGORY",
          "CATEGORIES EXPENSE (6-****)", "Category LK", "Category SPT"]


def row(smt=None, etf=None, exp=None, lk=None, spt=None):
    r = [None] * 15
    r[1], r[3], r[12], r[13], r[14] = smt, etf, exp, lk, spt
    return r


def sheet(*rows):
    return [[None] * 15, HEADER, *rows]


def as_map(rows):
    return {(r["source"], r["account"]): (r["categories_expense"], r["category_lk"], r["category_spt"])
            for r in rows}


# ---------- parse ----------

def test_maps_smt_and_etf_accounts_with_stripped_categories():
    rows = cm.normalise_categories(sheet(
        row("6-1810", None, " Office Supplies And Equipment Expense ", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1720", "6-2150", "Entertainment & Gift Expense", "HARGA POKOK PENJUALAN", "BIAYA LAINNYA")))
    assert as_map(rows) == {
        ("SMT", "6-1810"): ("Office Supplies And Equipment Expense", "Beban Operasional", "BIAYA LAINNYA"),
        ("SMT", "6-1720"): ("Entertainment & Gift Expense", "HARGA POKOK PENJUALAN", "BIAYA LAINNYA"),
        ("ETF", "6-2150"): ("Entertainment & Gift Expense", "HARGA POKOK PENJUALAN", "BIAYA LAINNYA"),
    }


def test_same_account_in_smt_and_etf_keeps_separate_categories():
    rows = cm.normalise_categories(sheet(
        row("6-1000", None, "", "Beban Operasional", "BIAYA LAINNYA"),
        row(None, "6-1000", "", "HARGA POKOK PENJUALAN", "BIAYA TRANSPORTASI")))
    assert as_map(rows) == {
        ("SMT", "6-1000"): ("", "Beban Operasional", "BIAYA LAINNYA"),
        ("ETF", "6-1000"): ("", "HARGA POKOK PENJUALAN", "BIAYA TRANSPORTASI"),
    }


def test_tba_is_normalised_and_zero_or_error_cells_are_empty():
    rows = cm.normalise_categories(sheet(
        row("6-1", None, "tba", "tba", "TBA"),
        row("6-2", None, 0.0, 0.0, "0x2a"),
        row("6-3", None, None, None, None)))
    # 6-2 (all cells 0 / error) and 6-3 (all empty) carry no category at all, so they are skipped
    assert as_map(rows) == {("SMT", "6-1"): ("TBA", "TBA", "TBA")}


def test_rows_without_any_account_are_skipped_and_duplicates_keep_first():
    rows = cm.normalise_categories(sheet(
        row(None, None, "x", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1", None, "a", "Beban Operasional", "BIAYA LAINNYA"),
        row("6-1", None, "b", "HARGA POKOK PENJUALAN", "BIAYA SEWA")))
    assert as_map(rows) == {("SMT", "6-1"): ("a", "Beban Operasional", "BIAYA LAINNYA")}


def test_numeric_account_is_text():
    rows = cm.normalise_categories(sheet(row(61810.0, None, "", "Beban Operasional", "BIAYA LAINNYA")))
    assert [r["account"] for r in rows] == ["61810"]


def test_wrong_header_or_empty_sheet_raises():
    bad = list(HEADER)
    bad[13] = "Kategori"
    with pytest.raises(CoaParseError, match="Category LK"):
        cm.normalise_categories([[None] * 15, bad])
    with pytest.raises(CoaParseError, match="kosong"):
        cm.normalise_categories([[None] * 15])


def test_is_unmapped():
    assert cm.is_unmapped("") and cm.is_unmapped("TBA") and cm.is_unmapped(" tba ")
    assert not cm.is_unmapped("BIAYA LAINNYA")


# ---------- storage ----------

RO = cm.normalise_categories(sheet(row("6-1810", None, "Office", "Beban Operasional", "BIAYA LAINNYA")))


def test_sync_stores_logs_and_second_identical_sync_is_unchanged():
    out = cm.sync_categories("GL - MASTER.xlsb", "admin", RO)
    assert out == {"changed": True, "rows_smt": 1, "rows_etf": 0}
    assert cm.get_category_map()[("SMT", "6-1810")] == {
        "categories_expense": "Office", "category_lk": "Beban Operasional", "category_spt": "BIAYA LAINNYA"}
    assert cm.last_sync()["filename"] == "GL - MASTER.xlsb"
    again = cm.sync_categories("GL - MASTER.xlsb", "admin", RO)
    assert again["changed"] is False and len(cm.list_syncs()) == 1


def test_sync_replaces_previous_rows_and_bumps_version():
    cm.sync_categories("a.xlsb", "admin", RO)
    v1 = cm.get_version()
    other = cm.normalise_categories(sheet(row("6-2000", None, "", "HARGA POKOK PENJUALAN", "BIAYA SEWA")))
    cm.sync_categories("b.xlsb", "admin", other)
    assert list(cm.get_category_map()) == [("SMT", "6-2000")]
    assert cm.get_version() == v1 + 1
    assert [s["filename"] for s in cm.list_syncs()] == ["b.xlsb", "a.xlsb"]


def test_failed_sync_keeps_previous_mapping():
    cm.sync_categories("a.xlsb", "admin", RO)
    with pytest.raises(KeyError):
        cm.sync_categories("b.xlsb", "admin", [{"source": "SMT", "account": "x"}])
    assert list(cm.get_category_map()) == [("SMT", "6-1810")]
    assert cm.last_sync()["filename"] == "a.xlsb"
