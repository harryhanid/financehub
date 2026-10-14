# tests/test_gl_real_file.py
"""Runs against the real GL - MASTER.xlsb when it is reachable; skipped otherwise."""
import os
import shutil

import pytest
from pyxlsb import open_workbook

from modules.general_ledger import service as svc
from modules.general_ledger import sync as glsync
from modules.general_ledger.parser import read_gl_sheet

SRC = r"Y:\Seagate\Management Report\2026\0926\GL - MASTER.xlsb"
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason="GL - MASTER.xlsb not reachable")


@pytest.fixture(scope="module")
def local_copy(tmp_path_factory):
    dst = tmp_path_factory.mktemp("glmaster") / "gl.xlsb"
    shutil.copy(SRC, dst)                      # the master is usually open in Excel
    return str(dst)


def control_totals(path, sheet):
    with open_workbook(path) as wb, wb.get_sheet(sheet) as sh:
        for row in sh.rows():
            vals = {c.c: c.v for c in row}
            return vals.get(10), vals.get(11)    # control row: total Debit, total Credit


@pytest.mark.parametrize("entity", ["smt", "etf", "setf"])
def test_real_sheet_matches_excel_control_row(local_copy, entity):
    sheet = svc.ENTITIES[entity]["sheet"]
    res = read_gl_sheet(local_copy, sheet)
    assert len(res.rows) > 100
    assert all(r["debit"] or r["credit"] for r in res.rows)             # zero/blank rows are not synced
    assert any(r["accrual_actual"] for r in res.rows)                    # the extra columns are really read
    assert any(r["category_lk"] for r in res.rows)
    ctl_debit, ctl_credit = control_totals(local_copy, sheet)
    assert abs(sum(r["debit"] for r in res.rows) - ctl_debit) < 1.0
    assert abs(sum(r["credit"] for r in res.rows) - ctl_credit) < 1.0
    out = glsync.sync_rows(entity, 2026, "GL - MASTER.xlsb", "test", res.rows, res.dropped)
    in_2026 = [r for r in res.rows if (r["tgl"] or "").startswith("2026-")]
    assert out["changed"] and out["rows"] == len(in_2026)
    if entity != "setf":                                                 # SETF's 2025 opening rows sit outside 2026
        assert out["balanced"]
    assert out["skipped_year"] == len(res.rows) - len(in_2026)           # e.g. GL SETF carries Nov-Dec 2025 rows
    assert svc.query_rows(entity, {"year": 2026})["total"] == len(in_2026)
    assert svc.query_rows(entity, {})["total"] == len(in_2026)
