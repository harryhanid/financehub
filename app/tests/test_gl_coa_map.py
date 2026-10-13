# tests/test_gl_coa_map.py
import pytest

from database import get_conn
from modules.general_ledger import coa_map as cm

HEADER = [None, "COA SMT", "Description", "COA ETF", "Description", "FROM :", "COA HO",
          "Sub Account", "CATEGORIES", "CATEGORIES 2", "Code", "BUDGET CATEGORY"]


def coa_row(smt=None, etf=None, coa_ho=None, cat=None):
    r = [None] * 12
    r[1], r[3], r[6], r[9] = smt, etf, coa_ho, cat
    return r


def sheet(*rows):
    return [[None] * 12, HEADER, *rows]


def as_set(rows):
    return {(r["source"], r["account"], r["coa_ho"], r["category"]) for r in rows}


def test_maps_smt_and_etf_accounts_with_stripped_category():
    rows = cm.normalise_coa(sheet(
        coa_row("6-1810", None, 70108100.0, " 10 - Office Supplies And Equipment Expense "),
        coa_row("6-1720", "6-2150", 70107200.0, " 06 - Entertainment & Gift Expense ")))
    assert as_set(rows) == {
        ("SMT", "6-1810", "70108100", "10 - Office Supplies And Equipment Expense"),
        ("SMT", "6-1720", "70107200", "06 - Entertainment & Gift Expense"),
        ("ETF", "6-2150", "70107200", "06 - Entertainment & Gift Expense"),
    }


def test_rows_without_coa_ho_or_with_error_cell_are_skipped():
    rows = cm.normalise_coa(sheet(
        coa_row("1-0000", None, None, None),
        coa_row("1-1000", None, "0x2a", None),
        coa_row("6-1810", None, 70108100.0, " 10 - X ")))
    assert [r["account"] for r in rows] == ["6-1810"]


def test_first_occurrence_of_an_account_wins():
    rows = cm.normalise_coa(sheet(
        coa_row("6-1810", None, 70108100.0, " 10 - A "),
        coa_row("6-1810", None, 99999999.0, " 99 - B ")))
    assert as_set(rows) == {("SMT", "6-1810", "70108100", "10 - A")}


def test_header_mismatch_raises():
    bad = sheet(coa_row("6-1810", None, 1.0, "x"))
    bad[1] = list(HEADER)
    bad[1][6] = "Something else"
    with pytest.raises(cm.CoaParseError, match="COA HO"):
        cm.normalise_coa(bad)


def test_too_short_sheet_raises():
    with pytest.raises(cm.CoaParseError):
        cm.normalise_coa([[None] * 12])


def rows_a():
    return [{"source": "SMT", "account": "6-1810", "coa_ho": "70108100", "category": "10 - Office"},
            {"source": "ETF", "account": "6-2190", "coa_ho": "70119100", "category": "20 - Others"}]


def table_count():
    conn = get_conn()
    try:
        cm.ensure_schema(conn)
        return conn.execute("SELECT COUNT(*) FROM gl_coa_map").fetchone()[0]
    finally:
        conn.close()


def test_sync_first_time_unchanged_then_changed():
    out = cm.sync_coa("m.xlsb", "admin", rows_a())
    assert out == {"changed": True, "rows_smt": 1, "rows_etf": 1}
    assert cm.get_map() == {("SMT", "6-1810"): ("70108100", "10 - Office"),
                            ("ETF", "6-2190"): ("70119100", "20 - Others")}
    assert cm.last_sync()["filename"] == "m.xlsb"

    assert cm.sync_coa("m.xlsb", "admin", rows_a())["changed"] is False

    changed = rows_a()
    changed[0]["coa_ho"] = "70108199"
    assert cm.sync_coa("m2.xlsb", "admin", changed)["changed"] is True
    assert cm.get_map()[("SMT", "6-1810")][0] == "70108199"


def test_resync_same_file_after_table_was_emptied_refills_it():
    cm.sync_coa("m.xlsb", "admin", rows_a())
    conn = get_conn()
    conn.execute("DELETE FROM gl_coa_map")
    conn.commit()
    conn.close()
    assert cm.sync_coa("m.xlsb", "admin", rows_a())["changed"] is True
    assert table_count() == 2


def test_failed_sync_keeps_previous_map():
    cm.sync_coa("m.xlsb", "admin", rows_a())
    with pytest.raises(KeyError):
        cm.sync_coa("bad.xlsb", "admin", [{"source": "SMT", "account": "x"}])
    assert table_count() == 2
    assert cm.last_sync()["filename"] == "m.xlsb"


def test_get_map_and_last_sync_when_never_synced():
    assert cm.get_map() == {}
    assert cm.last_sync() is None
