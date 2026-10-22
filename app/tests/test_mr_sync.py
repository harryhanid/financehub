import pytest

from database import get_conn
from modules.management_report import service as svc
from modules.management_report import sync as mrsync
from tests.test_mr_service import mkrow


def rows_a():
    return [
        mkrow(cc="AAA", category="01 - Rental", description="r1", mm1=1, bgt=10.0, pta=1.0, act=2.0),
        mkrow(cc="AAA", category="01 - Rental", description="r2", mm1=2, bgt=5.0, pta=0.0, act=0.0),
        mkrow(cc="BBB", category="02 - Travel", description="t1", mm1=1, bgt=7.0, pta=0.0, act=3.0),
    ]


# ---------- compute_hash ----------

def test_hash_ignores_row_order_and_float_noise():
    a = rows_a()
    b = list(reversed(rows_a()))
    b[0]["bgt"] = 7.0000000001
    assert mrsync.compute_hash(a) == mrsync.compute_hash(b)


def test_hash_changes_when_any_field_changes():
    base = mrsync.compute_hash(rows_a())
    for field, value in [("bgt", 11.0), ("act", 9.0), ("coa", "99999"), ("mm", 12),
                         ("description", "other"), ("cc", "ZZZ")]:
        changed = rows_a()
        changed[0][field] = value
        assert mrsync.compute_hash(changed) != base, field
    assert mrsync.compute_hash(rows_a()[:2]) != base


# ---------- summarize_changes ----------

def test_summary_counts_and_deltas():
    old = rows_a()
    new = rows_a()
    new[0]["act"] = 5.0                                      # changed line (AAA r1): act +3
    del new[1]                                               # removed line (AAA r2): bgt -5
    new.append(mkrow(cc="CCC", category="03 - New", description="n1", mm1=1, bgt=4.0, pta=0.5, act=0.0))
    s = mrsync.summarize_changes(old, new)
    assert (s["rows_before"], s["rows_after"]) == (3, 3)
    assert s["lines"] == {"added": 1, "removed": 1, "changed": 1}
    assert s["delta"] == {"bgt": -1.0, "pta": 0.5, "act": 3.0}
    by_cc = {c["cc"]: c for c in s["ccs"]}
    assert set(by_cc) == {"AAA", "CCC"}                      # BBB untouched
    assert (by_cc["AAA"]["bgt"], by_cc["AAA"]["act"]) == (-5.0, 3.0)
    assert (by_cc["AAA"]["removed"], by_cc["AAA"]["changed"], by_cc["AAA"]["added"]) == (1, 1, 0)
    assert (by_cc["CCC"]["added"], by_cc["CCC"]["bgt"], by_cc["CCC"]["pta"]) == (1, 4.0, 0.5)


def test_summary_aggregates_duplicate_lines_before_comparing():
    old = [mkrow(cc="AAA", description="d", bgt=3.0), mkrow(cc="AAA", description="d", bgt=2.0)]
    new = [mkrow(cc="AAA", description="d", bgt=5.0)]
    s = mrsync.summarize_changes(old, new)
    assert s["lines"] == {"added": 0, "removed": 0, "changed": 0}
    assert s["ccs"] == [] and (s["rows_before"], s["rows_after"]) == (2, 1)


def test_summary_against_empty_marks_everything_added():
    s = mrsync.summarize_changes([], rows_a())
    assert s["rows_before"] == 0 and s["lines"]["added"] == 3
    assert [c["cc"] for c in s["ccs"]] == ["AAA", "BBB"]


# ---------- sync_rows ----------

def test_first_sync_creates_active_snapshot_with_summary():
    res = mrsync.sync_rows(1, "Master.xlsb", "admin", rows_a())
    assert res["changed"] is True and res["rows"] == 3
    assert svc.get_active_upload_id(1) == res["upload_id"]
    assert res["summary"]["first"] is True
    assert svc.get_active_summary(1)["lines"]["added"] == 3


def test_second_sync_with_same_data_is_noop():
    first = mrsync.sync_rows(1, "Master.xlsb", "admin", rows_a())
    again = mrsync.sync_rows(1, "Master.xlsb", "admin", list(reversed(rows_a())))
    assert again == {"changed": False, "rows": 3}
    assert svc.get_active_upload_id(1) == first["upload_id"]
    assert len(svc.list_uploads(1)) == 1


def test_sync_with_changes_creates_new_snapshot_and_summary():
    first = mrsync.sync_rows(1, "Master.xlsb", "admin", rows_a())
    new = rows_a()
    new[2]["act"] = 8.0
    res = mrsync.sync_rows(1, "Master.xlsb", "admin", new)
    assert res["changed"] is True and res["upload_id"] != first["upload_id"]
    assert res["summary"]["first"] is False
    assert res["summary"]["lines"] == {"added": 0, "removed": 0, "changed": 1}
    assert res["summary"]["delta"]["act"] == 5.0
    assert svc.get_active_summary(1) == res["summary"]


def test_sync_is_per_company():
    mrsync.sync_rows(1, "a.xlsb", "admin", rows_a())
    res = mrsync.sync_rows(2, "a.xlsb", "admin", rows_a())    # other company: still a first sync
    assert res["changed"] is True and res["summary"]["first"] is True


def test_legacy_snapshot_without_hash_is_compared_by_content():
    up = svc.save_upload(1, "old.xlsb", "admin", rows_a())    # saved without content_hash
    assert mrsync.sync_rows(1, "new.xlsb", "admin", rows_a()) == {"changed": False, "rows": 3}
    assert svc.get_active_upload_id(1) == up


def test_static_schema_has_the_sync_columns():
    # Postgres: mr_upload comes from 0002_schema.sql with the columns old databases got by ALTER.
    conn = get_conn()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(mr_upload)")}
    conn.close()
    assert {"content_hash", "change_summary", "meta"} <= cols
    assert svc.list_uploads(1) == [] and svc.get_active_summary(1) is None
