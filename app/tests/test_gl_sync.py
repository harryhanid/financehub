# tests/test_gl_sync.py
import pytest

from database import get_conn
from modules.general_ledger import service as svc
from modules.general_ledger import sync as glsync


def mkrow(**kw):
    base = dict(entry_no=1, source_type="GJ", acc_statutory="6-1810", acc_statutory_desc="Office",
                acc_management="6-1810", acc_management_desc="Office", id_no="GJ-1",
                tgl="2026-01-02", memo="m", debit=10.0, credit=0.0, job_name="POCFAD",
                job_desc="", budget_activity="", customer_vendor="", allocation_memo="",
                event="", qty_awal=0.0, qty_akhir=0.0, uom="", nama_item="",
                harga_satuan=0.0, ket1="", ket2="", pph_non_pph="", debit_credit=0.0, period="",
                category_expense="", category_lk="", category_spt="", accrual_actual="", pph="",
                sub_category="", **{f"ket{i}": "" for i in range(3, 21)})
    base.update(kw)
    return base


def rows_a():
    return [mkrow(id_no="GJ-1", debit=10.0, credit=0.0),
            mkrow(id_no="GJ-1", acc_statutory="2-1110", debit=0.0, credit=10.0),
            mkrow(id_no="GJ-2", debit=5.0)]


def table_count(table):
    conn = get_conn()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


# ---------- hash / summary ----------

def test_hash_ignores_float_noise():
    b = rows_a()
    b[2]["debit"] = 5.0000000001                     # rows_a()[2] has debit 5.0
    assert glsync.compute_hash(rows_a()) == glsync.compute_hash(b)


def test_hash_changes_when_row_order_changes():
    assert glsync.compute_hash(list(reversed(rows_a()))) != glsync.compute_hash(rows_a())


def test_sync_rows_pure_reorder_counts_as_changed_and_follows_new_order():
    glsync.sync_rows("smt", 2026, "m.xlsb", "admin", rows_a())
    reordered = list(reversed(rows_a()))
    out = glsync.sync_rows("smt", 2026, "m.xlsb", "admin", reordered)
    assert out["changed"] is True
    assert [r["id_no"] for r in svc.load_rows("smt")] == ["GJ-2", "GJ-1", "GJ-1"]
    assert glsync.sync_rows("smt", 2026, "m.xlsb", "admin", reordered)["changed"] is False


def test_hash_changes_when_a_field_changes():
    base = glsync.compute_hash(rows_a())
    for field, value in [("debit", 11.0), ("memo", "x"), ("acc_statutory", "9-9"), ("tgl", "2026-02-02")]:
        changed = rows_a()
        changed[0][field] = value
        assert glsync.compute_hash(changed) != base, field
    assert glsync.compute_hash(rows_a()[:2]) != base


def test_summary_counts_added_removed_changed():
    old = rows_a()
    new = rows_a()
    new[2]["debit"] = 99.0                                   # GJ-2 amount changed
    new.append(mkrow(id_no="GJ-3", memo="new"))               # added
    del new[1]                                                # GJ-1 credit line removed
    s = glsync.summarize_changes(old, new)
    assert (s["added"], s["removed"], s["changed"]) == (1, 1, 1)


# ---------- storage ----------

def test_replace_all_replaces_and_logs():
    log = dict(synced_by="u", filename="a.xlsb", content_hash="h1", rows_before=0, rows_after=3,
               total_debit=15.0, total_credit=10.0, dropped=2, summary={"added": 3})
    svc.replace_year("smt", 2026, rows_a(), log)
    assert table_count("GLSMT") == 3
    svc.replace_year("smt", 2026, rows_a()[:1], dict(log, content_hash="h2", rows_after=1))
    assert table_count("GLSMT") == 1
    assert svc.last_sync("smt")["content_hash"] == "h2"
    assert [s["content_hash"] for s in svc.list_syncs("smt")] == ["h2", "h1"]
    assert svc.last_sync("etf") is None


def test_failed_replace_keeps_previous_data():
    log = dict(synced_by="u", filename="a.xlsb", content_hash="h1", rows_before=0, rows_after=3,
               total_debit=0, total_credit=0, dropped=0, summary={})
    svc.replace_year("smt", 2026, rows_a(), log)
    with pytest.raises(KeyError):
        svc.replace_year("smt", 2026, [{"id_no": "only-this"}], dict(log, content_hash="h2"))
    assert table_count("GLSMT") == 3
    assert svc.last_sync("smt")["content_hash"] == "h1"


def test_ensure_schema_rebuilds_legacy_table_with_other_columns():
    conn = get_conn()
    conn.execute("CREATE TABLE GLSMT (account_statutory TEXT, junk TEXT)")
    conn.execute("INSERT INTO GLSMT VALUES ('a','b')")
    conn.commit()
    conn.close()
    svc.replace_year("smt", 2026, rows_a(), dict(synced_by="u", filename="a", content_hash="h",
                                          rows_before=0, rows_after=3, total_debit=0,
                                          total_credit=0, dropped=0, summary={}))
    assert table_count("GLSMT") == 3


# ---------- sync_rows ----------

def test_sync_first_time_then_unchanged_then_changed():
    out = glsync.sync_rows("smt", 2026, "m.xlsb", "admin", rows_a(), dropped=4)
    assert out["changed"] is True and out["rows"] == 3
    assert out["total_debit"] == 15.0 and out["total_credit"] == 10.0 and out["balanced"] is False
    assert table_count("GLSMT") == 3

    again = glsync.sync_rows("smt", 2026, "m.xlsb", "admin", rows_a())
    assert again["changed"] is False
    assert len(svc.list_syncs("smt")) == 1                    # no extra log row

    changed = rows_a()
    changed[2]["memo"] = "edited"
    out = glsync.sync_rows("smt", 2026, "m2.xlsb", "admin", changed)
    assert out["changed"] is True
    last = svc.last_sync("smt")
    assert last["rows_before"] == 3 and last["rows_after"] == 3 and last["filename"] == "m2.xlsb"


def test_entities_are_independent():
    glsync.sync_rows("smt", 2026, "m.xlsb", "admin", rows_a())
    assert glsync.sync_rows("etf", 2026, "m.xlsb", "admin", rows_a())["changed"] is True
    assert table_count("GLETF") == 3 and table_count("GLSETF") == 0


def test_reading_never_destroys_a_legacy_table():
    conn = get_conn()
    conn.execute("CREATE TABLE GLSMT (account_statutory TEXT, junk TEXT)")
    conn.execute("INSERT INTO GLSMT VALUES ('a','b')")
    conn.commit()
    conn.close()
    assert svc.query_rows("smt", {})["total"] == 0          # a plain page view, no sync
    assert table_count("GLSMT_legacy") == 1                  # old data kept aside, not dropped


def test_resync_same_file_after_table_was_emptied_refills_it():
    glsync.sync_rows("smt", 2026, "m.xlsb", "admin", rows_a())
    conn = get_conn()
    conn.execute("DELETE FROM GLSMT")
    conn.commit()
    conn.close()
    out = glsync.sync_rows("smt", 2026, "m.xlsb", "admin", rows_a())
    assert out["changed"] is True and table_count("GLSMT") == 3


# ---------- multi-year ----------

def _log(**kw):
    return dict(dict(synced_by="u", filename="a.xlsb", content_hash="h", rows_before=0, rows_after=1,
                     total_debit=0, total_credit=0, dropped=0, summary={}), **kw)


def test_replace_year_only_replaces_that_year():
    svc.replace_year("smt", 2025, [mkrow(id_no="O1", tgl="2025-05-01")], _log(content_hash="h25"))
    svc.replace_year("smt", 2026, [mkrow(id_no="N1", tgl="2026-01-02"),
                                   mkrow(id_no="N2", tgl="2026-01-03")], _log(content_hash="h26"))
    svc.replace_year("smt", 2026, [mkrow(id_no="N3", tgl="2026-02-02")], _log(content_hash="h26b"))
    assert [r["id_no"] for r in svc.load_rows("smt")] == ["O1", "N3"]
    assert svc.row_count("smt", 2025) == 1 and svc.row_count("smt", 2026) == 1
    assert svc.row_count("smt") == 2


def test_replace_year_refuses_rows_of_another_year_and_keeps_data():
    svc.replace_year("smt", 2026, [mkrow(id_no="N1", tgl="2026-01-02")], _log())
    with pytest.raises(ValueError):
        svc.replace_year("smt", 2026, [mkrow(id_no="bad", tgl="2025-01-02")], _log(content_hash="h2"))
    assert [r["id_no"] for r in svc.load_rows("smt")] == ["N1"]


def test_sync_log_is_per_year():
    svc.replace_year("smt", 2025, [mkrow(tgl="2025-05-01")], _log(content_hash="h25"))
    svc.replace_year("smt", 2026, [mkrow(tgl="2026-05-01")], _log(content_hash="h26"))
    assert svc.last_sync("smt", 2025)["content_hash"] == "h25"
    assert svc.last_sync("smt", 2026)["content_hash"] == "h26"
    assert svc.last_sync("smt", 2024) is None
    assert [s["year"] for s in svc.list_syncs("smt")] == [2026, 2025]
    assert [s["year"] for s in svc.list_syncs("smt", 2025)] == [2025]


def test_years_with_data_and_latest_year():
    assert svc.years_with_data("smt") == [] and svc.latest_year("smt") is None
    svc.replace_year("smt", 2025, [mkrow(tgl="2025-05-01")], _log())
    svc.replace_year("smt", 2026, [mkrow(tgl="2026-05-01")], _log())
    assert svc.years_with_data("smt") == [2026, 2025] and svc.latest_year("smt") == 2026


def test_ensure_schema_adds_year_column_to_an_existing_log_table():
    conn = get_conn()
    conn.execute("DROP TABLE IF EXISTS gl_sync_log")
    conn.execute("CREATE TABLE gl_sync_log (id INTEGER PRIMARY KEY AUTOINCREMENT, entity TEXT NOT NULL, "
                 "synced_at TEXT, synced_by TEXT, filename TEXT, content_hash TEXT, rows_before INTEGER DEFAULT 0, "
                 "rows_after INTEGER DEFAULT 0, total_debit REAL DEFAULT 0, total_credit REAL DEFAULT 0, "
                 "dropped INTEGER DEFAULT 0, summary TEXT)")
    conn.execute("INSERT INTO gl_sync_log (entity, content_hash) VALUES ('smt', 'old')")
    conn.commit()
    conn.close()
    svc.replace_year("smt", 2026, [mkrow()], _log(content_hash="new"))
    logs = svc.list_syncs("smt")
    assert [(s["content_hash"], s["year"]) for s in logs] == [("new", 2026), ("old", None)]


def test_sync_rows_scopes_rows_to_the_year_and_counts_the_rest():
    rows = [mkrow(id_no="A", tgl="2025-12-31"), mkrow(id_no="B", tgl="2026-01-02"),
            mkrow(id_no="C", tgl=None)]
    out = glsync.sync_rows("smt", 2026, "m.xlsb", "admin", rows)
    assert out["rows"] == 1 and out["skipped_year"] == 2 and out["changed"] is True
    assert [r["id_no"] for r in svc.load_rows("smt")] == ["B"]


def test_sync_rows_is_unchanged_per_year_independently():
    r25 = [mkrow(id_no="A", tgl="2025-02-02")]
    r26 = [mkrow(id_no="B", tgl="2026-02-02")]
    assert glsync.sync_rows("smt", 2025, "a.xlsb", "admin", r25)["changed"] is True
    assert glsync.sync_rows("smt", 2026, "b.xlsb", "admin", r26)["changed"] is True
    assert glsync.sync_rows("smt", 2025, "a.xlsb", "admin", r25)["changed"] is False
    assert glsync.sync_rows("smt", 2026, "b.xlsb", "admin", r26)["changed"] is False
    assert table_count("GLSMT") == 2


def test_sync_rows_summary_compares_only_with_the_same_year():
    glsync.sync_rows("smt", 2025, "a.xlsb", "admin", [mkrow(id_no="A", tgl="2025-02-02")])
    out = glsync.sync_rows("smt", 2026, "b.xlsb", "admin", [mkrow(id_no="B", tgl="2026-02-02")])
    assert out["summary"] == {"added": 1, "removed": 0, "changed": 0}
    assert svc.last_sync("smt", 2026)["rows_before"] == 0


def test_sync_rows_without_any_row_in_the_year_raises_and_changes_nothing():
    glsync.sync_rows("smt", 2026, "a.xlsb", "admin", [mkrow(id_no="keep", tgl="2026-02-02")])
    with pytest.raises(glsync.NoRowsForYear):
        glsync.sync_rows("smt", 2025, "b.xlsb", "admin", [mkrow(tgl="2026-03-03")])
    assert [r["id_no"] for r in svc.load_rows("smt")] == ["keep"]
    assert svc.last_sync("smt", 2025) is None
