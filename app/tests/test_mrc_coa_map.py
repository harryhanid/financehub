# tests/test_gl_coa_map.py
import sqlite3

import pytest

from database import get_conn
from modules.management_report import coa_map as cm

HEADER = [None, "COA SMT", "Description", "COA ETF", "Description", "FROM :", "COA HO",
          "Sub Account", "CATEGORIES", "CATEGORIES 2", "Code", "BUDGET CATEGORY"]


def coa_row(smt=None, etf=None, coa_ho=None, cat=None, code=None):
    r = [None] * 12
    r[1], r[3], r[6], r[9], r[10] = smt, etf, coa_ho, cat, code
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


def test_code_column_is_mapped_and_numeric_zero_or_error_or_blank_gives_empty():
    rows = cm.normalise_coa(sheet(
        coa_row("6-1810", None, 70108100.0, " 10 - A ", "-10-"),
        coa_row("6-1720", None, 70107200.0, " 06 - B ", 0.0),
        coa_row("6-1730", None, 70107300.0, " 06 - B ", "0x2a"),
        coa_row("6-1740", None, 70107400.0, " 06 - B ", None)))
    assert {r["account"]: r["code"] for r in rows} == {
        "6-1810": "-10-", "6-1720": "", "6-1730": "", "6-1740": ""}


def test_header_requires_code_in_column_11():
    bad = sheet(coa_row("6-1810", None, 1.0, "x"))
    bad[1] = list(HEADER)
    bad[1][10] = "Other"
    with pytest.raises(cm.CoaParseError, match="Code"):
        cm.normalise_coa(bad)


def test_header_mismatch_raises():
    bad = sheet(coa_row("6-1810", None, 1.0, "x"))
    bad[1] = list(HEADER)
    bad[1][6] = "Something else"
    with pytest.raises(cm.CoaParseError, match="COA HO"):
        cm.normalise_coa(bad)


def test_too_short_sheet_raises():
    with pytest.raises(cm.CoaParseError):
        cm.normalise_coa([[None] * 12])


CC_HEADER = [None, "Cost Center", "Cost Center Description", "Cost Center TOTAL", None, None]


def cc_row(cc=None, desc=None, total=None, seq=None, extra=None):
    r = [None, cc, desc, total, None, seq]
    if extra is not None:
        r.append(extra)
    return r


def cc_sheet(*rows):
    return [[None] * 6, CC_HEADER, *rows]


def test_normalise_cc_happy_path():
    rows = cm.normalise_cc(cc_sheet(
        cc_row(" POITEC ", "IT", "$POITEC", 16.0, extra="junk right of col 5"),
        cc_row("POITEC", "dup", "$OTHER", 99.0),
        cc_row("TFOPEX", "Opex", None, None),
        cc_row("TFX", "X", "0x2a", "abc"),
        cc_row(None, "no cost center", "$Z", 5.0),
        cc_row("0x2a", "err cost center", "$Z", 5.0)))
    assert rows == [
        {"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": "IT"},
        {"cost_center": "TFOPEX", "total_cc": "", "seq": 0, "description": "Opex"},
        {"cost_center": "TFX", "total_cc": "", "seq": 0, "description": "X"}]
    assert isinstance(rows[0]["seq"], int)


@pytest.mark.parametrize("pos,label", [(1, "Cost Center"), (2, "Cost Center Description"),
                                       (3, "Cost Center TOTAL")])
def test_normalise_cc_header_mismatch_names_expected_label(pos, label):
    bad = cc_sheet(cc_row("A", "d", "$A", 1.0))
    bad[1] = list(CC_HEADER)
    bad[1][pos] = "Wrong"
    with pytest.raises(cm.CoaParseError, match=label):
        cm.normalise_cc(bad)


def test_normalise_cc_header_is_case_and_space_insensitive():
    ok = cc_sheet(cc_row("A", "d", "$A", 1.0))
    ok[1] = [None, " cost  center", "COST CENTER description", "cost center total"]
    assert cm.normalise_cc(ok)[0]["cost_center"] == "A"


def test_normalise_cc_too_short_raises():
    with pytest.raises(cm.CoaParseError):
        cm.normalise_cc([[None] * 6])


def rows_a():
    return [{"source": "SMT", "account": "6-1810", "coa_ho": "70108100", "category": "10 - Office",
             "code": "-10-"},
            {"source": "ETF", "account": "6-2190", "coa_ho": "70119100", "category": "20 - Others",
             "code": "-20-"}]


def cc_a():
    return [{"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": "IT"},
            {"cost_center": "PULPP", "total_cc": "", "seq": 0, "description": "Pulpp"}]


def count(table):
    conn = get_conn()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def table_count():
    return count("gl_coa_map")


def test_sync_first_time_unchanged_then_changed():
    out = cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a())
    assert out == {"changed": True, "rows_smt": 1, "rows_etf": 1, "rows_cc": 2}
    assert cm.get_map() == {("SMT", "6-1810"): ("70108100", "10 - Office", "-10-"),
                            ("ETF", "6-2190"): ("70119100", "20 - Others", "-20-")}
    assert cm.get_cc_map() == {"POITEC": {"total": "$POITEC", "seq": 16, "description": "IT"},
                               "PULPP": {"total": "", "seq": 0, "description": "Pulpp"}}
    last = cm.last_sync()
    assert last["filename"] == "m.xlsb" and last["rows_cc"] == 2

    assert cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a()) == {
        "changed": False, "rows_smt": 1, "rows_etf": 1, "rows_cc": 2}

    changed = rows_a()
    changed[0]["coa_ho"] = "70108199"
    assert cm.sync_coa("m2.xlsb", "admin", changed, cc_a())["changed"] is True
    assert cm.get_map()[("SMT", "6-1810")][0] == "70108199"


def test_changed_code_or_cc_row_counts_as_change():
    cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a())
    code = rows_a()
    code[0]["code"] = "-11-"
    assert cm.sync_coa("m.xlsb", "admin", code, cc_a())["changed"] is True
    assert cm.get_map()[("SMT", "6-1810")][2] == "-11-"
    cc = cc_a()
    cc[0]["seq"] = 17
    assert cm.sync_coa("m.xlsb", "admin", code, cc)["changed"] is True
    assert cm.get_cc_map()["POITEC"]["seq"] == 17
    assert cm.sync_coa("m.xlsb", "admin", code, cc[:1])["changed"] is True
    assert list(cm.get_cc_map()) == ["POITEC"]


def test_rows_without_code_key_and_no_cc_rows_still_work():
    old = [{"source": "SMT", "account": "6-1810", "coa_ho": "70108100", "category": "10 - Office"}]
    assert cm.sync_coa("m.xlsb", "admin", old) == {
        "changed": True, "rows_smt": 1, "rows_etf": 0, "rows_cc": 0}
    assert cm.get_map() == {("SMT", "6-1810"): ("70108100", "10 - Office", "")}
    assert cm.get_cc_map() == {}
    assert cm.sync_coa("m.xlsb", "admin", old)["changed"] is False


def test_resync_same_file_after_table_was_emptied_refills_it():
    cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a())
    conn = get_conn()
    conn.execute("DELETE FROM gl_coa_map")
    conn.commit()
    conn.close()
    assert cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a())["changed"] is True
    assert table_count() == 2


def test_resync_same_file_after_cc_table_was_emptied_refills_it():
    cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a())
    conn = get_conn()
    conn.execute("DELETE FROM gl_cc_map")
    conn.commit()
    conn.close()
    assert cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a())["changed"] is True
    assert count("gl_cc_map") == 2


def _state():
    conn = get_conn()
    try:
        logs = conn.execute("SELECT filename, content_hash FROM gl_coa_sync_log "
                            "ORDER BY id").fetchall()
        return cm.get_map(), cm.get_cc_map(), [tuple(r) for r in logs]
    finally:
        conn.close()


def test_failed_sync_rolls_back_everything_when_cc_insert_violates_primary_key():
    cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a())
    before = _state()
    new = rows_a()
    new[0]["coa_ho"] = "1"
    dup_cc = [{"cost_center": "X", "total_cc": "", "seq": 1, "description": ""},
              {"cost_center": "X", "total_cc": "", "seq": 2, "description": ""}]
    with pytest.raises(sqlite3.IntegrityError):
        cm.sync_coa("bad.xlsb", "admin", new, dup_cc)
    assert _state() == before
    assert cm.get_map()[("SMT", "6-1810")][0] == "70108100"
    assert set(cm.get_cc_map()) == {"POITEC", "PULPP"}
    assert cm.last_sync()["filename"] == "m.xlsb"


def test_failed_sync_rolls_back_when_coa_insert_violates_primary_key():
    cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a())
    before = _state()
    dup = rows_a() + rows_a()[:1]
    with pytest.raises(sqlite3.IntegrityError):
        cm.sync_coa("bad.xlsb", "admin", dup, [])
    assert _state() == before


def test_failed_sync_rolls_back_when_log_insert_fails(monkeypatch):
    cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a())
    before = _state()
    real_get_conn = cm.get_conn

    class Proxy:
        def __init__(self, conn):
            self._c = conn

        def batch(self, items):
            if any(sql.lstrip().startswith("INSERT INTO gl_coa_sync_log") for sql, _ in items):
                raise RuntimeError("log insert failed")
            return self._c.batch(items)

        def __getattr__(self, name):
            return getattr(self._c, name)

    monkeypatch.setattr(cm, "get_conn", lambda: Proxy(real_get_conn()))
    changed = rows_a()
    changed[0]["coa_ho"] = "2"
    with pytest.raises(RuntimeError, match="log insert failed"):
        cm.sync_coa("bad.xlsb", "admin", changed, cc_a()[:1])
    monkeypatch.setattr(cm, "get_conn", real_get_conn)
    assert _state() == before


def test_get_map_and_last_sync_when_never_synced():
    assert cm.get_map() == {}
    assert cm.get_cc_map() == {}
    assert cm.last_sync() is None


def test_static_schema_has_the_columns_old_databases_got_by_migration():
    # Postgres: the tables come from 0002_schema.sql (no runtime CREATE/ALTER any more).
    conn = get_conn()
    try:
        coa = {r[1] for r in conn.execute("PRAGMA table_info(gl_coa_map)")}
        log = {r[1] for r in conn.execute("PRAGMA table_info(gl_coa_sync_log)")}
    finally:
        conn.close()
    assert "code" in coa and "rows_cc" in log
    assert cm.sync_coa("new.xlsb", "admin", rows_a(), cc_a()) == {
        "changed": True, "rows_smt": 1, "rows_etf": 1, "rows_cc": 2}
    assert cm.get_map()[("SMT", "6-1810")] == ("70108100", "10 - Office", "-10-")
    assert cm.last_sync()["rows_cc"] == 2


class _Cell:
    def __init__(self, v):
        self.v = v


class _FakeSheet:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def rows(self):
        return [[_Cell(v) for v in r] for r in self._rows]


class _FakeWb:
    def __init__(self, sheets):
        self._s = sheets
        self.sheets = list(sheets)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_sheet(self, name):
        return _FakeSheet(self._s[name])


def test_read_mapping_sheets_returns_both_tables(monkeypatch):
    wb = _FakeWb({"COA": sheet(coa_row("6-1810", None, 70108100.0, " 10 - A ", "-10-")),
                  "CC": cc_sheet(cc_row("POITEC", "IT", "$POITEC", 16.0))})
    monkeypatch.setattr(cm, "open_workbook", lambda f: wb)
    coa, cc = cm.read_mapping_sheets(object())
    assert coa == [{"source": "SMT", "account": "6-1810", "coa_ho": "70108100",
                    "category": "10 - A", "code": "-10-"}]
    assert cc == [{"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16,
                   "description": "IT"}]


def test_read_mapping_sheets_missing_sheet_message(monkeypatch):
    wb = _FakeWb({"COA": sheet(coa_row("6-1810", None, 70108100.0, " 10 - A ", "-10-"))})
    monkeypatch.setattr(cm, "open_workbook", lambda f: wb)
    with pytest.raises(cm.CoaParseError) as e:
        cm.read_mapping_sheets(object())
    assert str(e.value) == "Sheet 'CC' tidak ditemukan di file."
    wb2 = _FakeWb({"CC": cc_sheet()})
    monkeypatch.setattr(cm, "open_workbook", lambda f: wb2)
    with pytest.raises(cm.CoaParseError) as e:
        cm.read_mapping_sheets(object())
    assert str(e.value) == "Sheet 'COA' tidak ditemukan di file."


def test_read_mapping_sheets_wraps_unreadable_file():
    import io
    with pytest.raises(cm.CoaParseError, match="tidak bisa dibaca"):
        cm.read_mapping_sheets(io.BytesIO(b"not an xlsb"))


def test_read_mapping_sheets_wraps_unexpected_normalise_errors(monkeypatch):
    wb = _FakeWb({"COA": sheet(coa_row("6-1810", None, 70108100.0, " 10 - A ", "-10-")),
                  "CC": cc_sheet(cc_row("POITEC", "IT", "$POITEC", 16.0))})
    monkeypatch.setattr(cm, "open_workbook", lambda f: wb)

    def boom(rows):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(cm, "normalise_cc", boom)
    with pytest.raises(cm.CoaParseError, match="kaboom"):
        cm.read_mapping_sheets(object())


def test_infinite_or_nan_seq_cell_becomes_zero():
    rows = cm.normalise_cc(cc_sheet(cc_row("A", "d", "$A", float("inf")),
                                    cc_row("B", "d", "$B", float("nan"))))
    assert [r["seq"] for r in rows] == [0, 0]


def test_read_coa_sheet_wraps_unexpected_normalise_errors(monkeypatch):
    wb = _FakeWb({"COA": sheet(coa_row("6-1810", None, 70108100.0, " 10 - A ", "-10-"))})
    monkeypatch.setattr(cm, "open_workbook", lambda f: wb)

    def boom(rows):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(cm, "normalise_coa", boom)
    with pytest.raises(cm.CoaParseError, match="kaboom"):
        cm.read_coa_sheet(object())


# ---- read helpers for the Pemetaan tab: list_syncs / search_coa / search_cc ----

def _coa_seed():
    return [
        {"source": "SMT", "account": "6-1810", "coa_ho": "70108100", "category": "10 - Office Supplies", "code": "-10-"},
        {"source": "SMT", "account": "6-1720", "coa_ho": "70107200", "category": "06 - Entertainment & Gift", "code": "-06-"},
        {"source": "ETF", "account": "6-2150", "coa_ho": "70107200", "category": "06 - Entertainment & Gift", "code": "-06-"},
        {"source": "ETF", "account": "6-1810", "coa_ho": "70108155", "category": "10 - office supplies", "code": "-10-"},
        {"source": "SMT", "account": "6-3000", "coa_ho": "70130000", "category": "30 - Travel", "code": "-30-"},
    ]


def _accounts(result):
    return [(r["source"], r["account"]) for r in result["rows"]]


def test_list_syncs_empty_before_any_sync():
    assert cm.list_syncs() == []


def test_list_syncs_newest_first_with_counts_and_limit():
    cm.sync_coa("one.xlsb", "admin", rows_a(), cc_a())
    two = rows_a()
    two[0]["coa_ho"] = "1"
    cm.sync_coa("two.xlsb", "boss", two, cc_a()[:1])
    cm.sync_coa("three.xlsb", "admin", two[:1], [])
    out = cm.list_syncs()
    assert [(s["filename"], s["synced_by"], s["rows_smt"], s["rows_etf"], s["rows_cc"])
            for s in out] == [("three.xlsb", "admin", 1, 0, 0),
                              ("two.xlsb", "boss", 1, 1, 1),
                              ("one.xlsb", "admin", 1, 1, 2)]
    assert out[0]["id"] > out[1]["id"] > out[2]["id"]
    assert set(out[0]) == {"id", "synced_at", "synced_by", "filename", "content_hash",
                           "rows_smt", "rows_etf", "rows_cc"}
    assert [s["filename"] for s in cm.list_syncs(limit=2)] == ["three.xlsb", "two.xlsb"]
    assert [s["filename"] for s in cm.list_syncs(limit=0)] == ["three.xlsb"]
    assert [s["filename"] for s in cm.list_syncs(limit=-5)] == ["three.xlsb"]


def test_list_syncs_null_rows_cc_becomes_zero():
    conn = get_conn()
    conn.execute("INSERT INTO gl_coa_sync_log (filename, content_hash, rows_smt, rows_etf, rows_cc) "
                 "VALUES ('old.xlsb', 'h', 3, 4, NULL)")
    conn.commit()
    conn.close()
    out = cm.list_syncs()
    assert len(out) == 1 and out[0]["rows_cc"] == 0 and out[0]["rows_smt"] == 3


def test_search_coa_empty_database():
    assert cm.search_coa() == {"rows": [], "total": 0, "page": 1, "pages": 1, "per_page": 100}


def test_search_coa_unfiltered_sorted_and_source_filter():
    cm.sync_coa("m.xlsb", "admin", _coa_seed())
    out = cm.search_coa()
    assert _accounts(out) == [("ETF", "6-1810"), ("ETF", "6-2150"), ("SMT", "6-1720"),
                              ("SMT", "6-1810"), ("SMT", "6-3000")]
    assert out["total"] == 5 and out["page"] == 1 and out["pages"] == 1 and out["per_page"] == 100
    assert out["rows"][3] == {"source": "SMT", "account": "6-1810", "coa_ho": "70108100",
                              "category": "10 - Office Supplies", "code": "-10-"}
    assert _accounts(cm.search_coa(source="ETF")) == [("ETF", "6-1810"), ("ETF", "6-2150")]
    assert cm.search_coa(source="SMT")["total"] == 3
    assert cm.search_coa(source="NOPE")["total"] == 5
    assert cm.search_coa(source="smt")["total"] == 5   # only exact "SMT"/"ETF"


def test_search_coa_q_over_each_field_case_insensitive_and_trimmed():
    cm.sync_coa("m.xlsb", "admin", _coa_seed())
    assert _accounts(cm.search_coa(q="6-3000")) == [("SMT", "6-3000")]
    assert _accounts(cm.search_coa(q="70108155")) == [("ETF", "6-1810")]
    assert _accounts(cm.search_coa(q="TRAVEL")) == [("SMT", "6-3000")]
    assert _accounts(cm.search_coa(q="office supplies")) == [("ETF", "6-1810"), ("SMT", "6-1810")]
    assert _accounts(cm.search_coa(q="-10-")) == [("ETF", "6-1810"), ("SMT", "6-1810")]
    assert _accounts(cm.search_coa(q="  -06-  ")) == [("ETF", "6-2150"), ("SMT", "6-1720")]
    assert _accounts(cm.search_coa(q="gift", source="ETF")) == [("ETF", "6-2150")]
    assert cm.search_coa(q="   ")["total"] == 5
    assert cm.search_coa(q=None)["total"] == 5
    assert cm.search_coa(q="%")["total"] == 0          # LIKE wildcard is literal


def test_search_coa_no_match():
    cm.sync_coa("m.xlsb", "admin", _coa_seed())
    assert cm.search_coa(q="zzz") == {"rows": [], "total": 0, "page": 1, "pages": 1,
                                      "per_page": 100}


def test_search_coa_pagination_and_clamping():
    cm.sync_coa("m.xlsb", "admin", _coa_seed())
    p1 = cm.search_coa(per_page=2)
    assert (p1["total"], p1["pages"], p1["page"], p1["per_page"]) == (5, 3, 1, 2)
    assert _accounts(p1) == [("ETF", "6-1810"), ("ETF", "6-2150")]
    assert _accounts(cm.search_coa(page=2, per_page=2)) == [("SMT", "6-1720"), ("SMT", "6-1810")]
    last = cm.search_coa(page=3, per_page=2)
    assert _accounts(last) == [("SMT", "6-3000")] and last["page"] == 3
    for bad, want in ((0, 1), (-3, 1), (999, 3)):
        out = cm.search_coa(page=bad, per_page=2)
        assert out["page"] == want and out["pages"] == 3
    assert _accounts(cm.search_coa(page=999, per_page=2)) == [("SMT", "6-3000")]
    assert _accounts(cm.search_coa(page=0, per_page=2)) == _accounts(p1)


def _cc_seed():
    return [{"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16, "description": "IT Dept"},
            {"cost_center": "alpha", "total_cc": "$GRP", "seq": 2, "description": "Alpha Unit"},
            {"cost_center": "TFOPEX", "total_cc": "", "seq": 0, "description": "Opex"},
            {"cost_center": "PULPP", "total_cc": "$GRP", "seq": 7, "description": "Pulpp"},
            {"cost_center": "ZED", "total_cc": "$Z", "seq": 123, "description": "Last"}]


def _ccs(result):
    return [r["cost_center"] for r in result["rows"]]


def test_search_cc_empty_database():
    assert cm.search_cc() == {"rows": [], "total": 0, "page": 1, "pages": 1, "per_page": 100}


def test_search_cc_sorted_and_q_over_each_field():
    cm.sync_coa("m.xlsb", "admin", [], _cc_seed())
    out = cm.search_cc()
    assert _ccs(out) == ["POITEC", "PULPP", "TFOPEX", "ZED", "alpha"]   # plain string order
    assert out["rows"][0] == {"cost_center": "POITEC", "total_cc": "$POITEC", "seq": 16,
                              "description": "IT Dept"}
    assert out["total"] == 5 and out["pages"] == 1 and out["page"] == 1 and out["per_page"] == 100
    assert _ccs(cm.search_cc(q="poi")) == ["POITEC"]
    assert _ccs(cm.search_cc(q="$grp")) == ["PULPP", "alpha"]
    assert _ccs(cm.search_cc(q="  unit ")) == ["alpha"]
    assert _ccs(cm.search_cc(q="123")) == ["ZED"]
    assert _ccs(cm.search_cc(q="16")) == ["POITEC"]
    assert cm.search_cc(q="")["total"] == 5
    assert cm.search_cc(q=None)["total"] == 5
    assert cm.search_cc(q="nothing") == {"rows": [], "total": 0, "page": 1, "pages": 1,
                                         "per_page": 100}


def test_search_cc_pagination_and_clamping():
    cm.sync_coa("m.xlsb", "admin", [], _cc_seed())
    assert _ccs(cm.search_cc(per_page=2)) == ["POITEC", "PULPP"]
    assert _ccs(cm.search_cc(page=2, per_page=2)) == ["TFOPEX", "ZED"]
    last = cm.search_cc(page=3, per_page=2)
    assert _ccs(last) == ["alpha"] and (last["page"], last["pages"], last["total"]) == (3, 3, 5)
    for bad, want in ((0, 1), (-3, 1), (999, 3)):
        out = cm.search_cc(page=bad, per_page=2)
        assert out["page"] == want and out["pages"] == 3
    assert _ccs(cm.search_cc(page=999, per_page=2)) == ["alpha"]


# ---------- Postgres atomicity (one batch per flow) ----------

def test_sync_coa_atomic_on_failure(monkeypatch):
    from tests.test_mr_service import fail_batch_after_writes
    cm.sync_coa("m.xlsb", "admin", rows_a(), cc_a())
    before = (_state(), count("gl_coa_map"), count("gl_cc_map"), count("gl_coa_sync_log"))
    fail_batch_after_writes(monkeypatch, "INSERT INTO gl_coa_sync_log")
    changed = rows_a()
    changed[0]["coa_ho"] = "3"
    with pytest.raises(Exception):
        cm.sync_coa("bad.xlsb", "admin", changed, cc_a()[:1])
    assert (_state(), count("gl_coa_map"), count("gl_cc_map"), count("gl_coa_sync_log")) == before


def test_sync_coa_batch_starts_with_the_advisory_lock_and_handles_many_rows(monkeypatch):
    from fhdb.connection import Connection
    batches = []
    real = Connection.batch

    def spy(self, items):
        batches.append(list(items))
        return real(self, items)
    monkeypatch.setattr(Connection, "batch", spy)
    rows = [{"source": "SMT", "account": f"6-{i:05d}", "coa_ho": "70108100", "category": "c",
             "code": ""} for i in range(2300)]
    assert cm.sync_coa("m.xlsb", "admin", rows, cc_a())["changed"] is True
    swap = batches[-1]
    assert swap[0] == ("SELECT pg_advisory_xact_lock(hashtext(?))", ("mr:coa_map",))
    assert sum(1 for sql, _ in swap if sql.startswith('INSERT INTO "gl_coa_map"')) == 3
    assert count("gl_coa_map") == 2300 and count("gl_cc_map") == 2
