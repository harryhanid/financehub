import io
import os

import pytest

from modules.management_report import service as svc
from modules.management_report import sync as mrsync
from modules.management_report.parser import build_meta, read_meta
from tests.test_mr_service import mkrow

META = {"cc_names": {"AAA": "Alpha Unit"}, "period": "2026-08-31"}
SAMPLE = os.environ.get('MR_SAMPLE_XLSB',
                        r'C:\Users\25010160\Downloads\Management Report - MASTER.xlsb')


def rows_a():
    return [mkrow(cc="AAA", description="r1", bgt=10.0), mkrow(cc="BBB", description="t1", bgt=7.0)]


def test_build_meta_keeps_names_and_converts_the_excel_serial_date():
    m = build_meta([("POCCOM", "Corporate Communication"), (None, None), ("0xf", "0xf"),
                    ("X", ""), (" POEAMR ", " External Affairs ")], 46265.0)
    assert m == {"cc_names": {"POCCOM": "Corporate Communication", "POEAMR": "External Affairs"},
                 "period": "2026-08-31"}


def test_build_meta_tolerates_a_missing_or_bad_period():
    assert build_meta([], None)["period"] is None
    assert build_meta([], "garbage")["period"] is None


def test_read_meta_of_a_non_workbook_is_empty():
    assert read_meta(io.BytesIO(b"x")) == {"cc_names": {}, "period": None}


def test_read_meta_from_the_real_master_workbook():
    try:
        with open(SAMPLE, 'rb') as f:
            data = f.read()
    except OSError:
        pytest.skip('sample master workbook not available')
    meta = read_meta(io.BytesIO(data))
    assert len(meta["cc_names"]) >= 30
    assert meta["cc_names"].get("TFKHAR") == "Ketua Harian"
    assert meta["period"] and meta["period"].startswith("20")


def test_hash_is_unchanged_without_metadata_and_changes_with_it():
    plain = mrsync.compute_hash(rows_a())
    assert plain == mrsync.compute_hash(rows_a(), None)
    assert plain == mrsync.compute_hash(rows_a(), {"cc_names": {}, "period": None})
    assert mrsync.compute_hash(rows_a(), META) != plain
    other = {"cc_names": {"AAA": "Alpha Unit"}, "period": "2026-09-30"}
    assert mrsync.compute_hash(rows_a(), other) != mrsync.compute_hash(rows_a(), META)


def test_metadata_is_stored_per_company():
    mrsync.sync_rows(1, "m.xlsb", "admin", rows_a(), meta=META)
    assert svc.get_active_meta(1) == META
    assert svc.get_active_meta(2) == {"cc_names": {}, "period": None}


def test_same_rows_and_meta_is_a_noop_but_a_meta_change_is_a_change():
    mrsync.sync_rows(1, "m.xlsb", "admin", rows_a(), meta=META)
    assert mrsync.sync_rows(1, "m.xlsb", "admin", rows_a(), meta=dict(META)) == \
        {"changed": False, "rows": 2}
    renamed = {"cc_names": {"AAA": "Alpha Renamed"}, "period": "2026-08-31"}
    res = mrsync.sync_rows(1, "m.xlsb", "admin", rows_a(), meta=renamed)
    assert res["changed"] is True and res["summary"]["meta_changed"] is True
    assert res["summary"]["lines"] == {"added": 0, "removed": 0, "changed": 0}
    assert svc.get_active_meta(1)["cc_names"]["AAA"] == "Alpha Renamed"


def test_first_sync_is_not_reported_as_a_meta_change():
    res = mrsync.sync_rows(1, "m.xlsb", "admin", rows_a(), meta=META)
    assert res["summary"]["meta_changed"] is False


def test_snapshot_saved_before_metadata_existed_gets_it_on_the_next_sync():
    svc.save_upload(1, "old.xlsb", "admin", rows_a())          # no metadata, no hash
    res = mrsync.sync_rows(1, "new.xlsb", "admin", rows_a(), meta=META)
    assert res["changed"] is True and res["summary"]["meta_changed"] is True
    assert mrsync.sync_rows(1, "new.xlsb", "admin", rows_a(), meta=META)["changed"] is False


def test_empty_metadata_never_wipes_the_stored_one():
    mrsync.sync_rows(1, "m.xlsb", "admin", rows_a(), meta=META)
    empty = {"cc_names": {}, "period": None}
    assert mrsync.sync_rows(1, "m.xlsb", "admin", rows_a(), meta=empty) == {"changed": False, "rows": 2}
    assert svc.get_active_meta(1) == META
    changed_rows = rows_a()
    changed_rows[0]["bgt"] = 11.0
    res = mrsync.sync_rows(1, "m.xlsb", "admin", changed_rows, meta=None)
    assert res["changed"] is True and res["summary"]["meta_changed"] is False
    assert svc.get_active_meta(1) == META                 # carried forward into the new snapshot
