# tests/test_mrc_category_real_file.py
import os
import shutil

import pytest

from modules.general_ledger import service as gl_service
from modules.general_ledger.parser import read_gl_sheet
from modules.management_report import category_map as cm

SRC = r"Y:\Seagate\Management Report\2026\0926\GL - MASTER.xlsb"
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason="GL - MASTER.xlsb not available")


@pytest.fixture(scope="module")
def local_copy(tmp_path_factory):
    dst = tmp_path_factory.mktemp("glmaster") / "GL - MASTER.xlsb"
    shutil.copyfile(SRC, dst)
    return str(dst)


def test_real_coa_sheet_matches_the_categories_on_every_gl_row(local_copy):
    rows = cm.read_category_sheet(local_copy)
    assert len(rows) > 400
    cm.sync_categories("GL - MASTER.xlsb", "test", rows)
    cmap = cm.get_category_map()
    gl = read_gl_sheet(local_copy, "GL SMT")
    mismatch, missing = 0, set()
    for r in gl.rows:
        entry = cmap.get(("SMT", r["acc_statutory"]))
        if entry is None:
            missing.add(r["acc_statutory"])
        elif (entry["category_lk"], entry["category_spt"]) != (r["category_lk"], r["category_spt"]):
            mismatch += 1
    assert mismatch == 0 and not missing


def test_real_sheet_seeds_every_known_lk_with_a_report_type(local_copy):
    cm.sync_categories("GL - MASTER.xlsb", "test", cm.read_category_sheet(local_copy))
    lk = cm.get_lk_list()
    assert lk["Jasa Konsultasi & Advokasi"]["kind"] == "pendapatan"
    assert "TBA" not in lk and "tba" not in lk
    unknown = [n for n, m in lk.items() if not m["statement"]]
    assert unknown == []          # every category in the real sheet has a default report type
