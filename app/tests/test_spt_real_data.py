# tests/test_spt_real_data.py
import os
import shutil

import pytest

from modules.general_ledger import sync as gl_sync
from modules.general_ledger.parser import read_gl_sheet
from modules.management_report import category_map as cm
from modules.spt_badan import service as sv

SRC = r"Y:\Seagate\Management Report\2026\0926\GL - MASTER.xlsb"
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason="GL - MASTER.xlsb not available")


@pytest.fixture(scope="module")
def local_copy(tmp_path_factory):
    dst = tmp_path_factory.mktemp("glmaster") / "GL - MASTER.xlsb"
    shutil.copyfile(SRC, dst)
    return str(dst)


def test_real_smt_2026_snapshot(local_copy):
    cm.sync_categories("GL - MASTER.xlsb", "test", cm.read_category_sheet(local_copy))
    res = read_gl_sheet(local_copy, "GL SMT")
    gl_sync.sync_rows("smt", 2026, "GL - MASTER.xlsb", "test", res.rows, res.dropped)
    pid = sv.create_period("smt", 2026, "test")
    sid = sv.take_snapshot(pid, "test")
    period, snap = sv.get_period(pid), sv.get_current_snapshot(pid)
    ctrls = {c["code"]: c for c in sv.get_controls(period, snap)}
    for code in ("C1", "C2", "C3", "C4", "C5", "C6", "C8"):
        assert ctrls[code]["status"] == "lulus", (code, ctrls[code])
    assert ctrls["C7"]["status"] == "peringatan"                  # the GL's PPh column is not clean yet
    summary = sv.income_statement_for(sid)["summary"]
    assert summary["revenue"] > 50e9 and summary["hpp"] > 30e9
    assert summary["pbt"] == pytest.approx(summary["gross"] - summary["opex"] + summary["other"])
    kinds = {g["kind"] for g in sv.exception_groups(sid)}
    assert {"pph_kosong", "pph_bukan_jenis"} <= kinds
    assert not kinds & {"akun_belum_dipetakan", "category_lk_tidak_dikenal", "category_spt_kosong"}
