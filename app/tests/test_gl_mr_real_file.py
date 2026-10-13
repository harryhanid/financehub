# tests/test_gl_mr_real_file.py
"""Compares the MR rows we derive with the real workbooks; skipped when they are not reachable."""
import os
import shutil
from collections import Counter

import pytest
from pyxlsb import open_workbook

from modules.general_ledger import coa_map
from modules.general_ledger.mr_rows import build_mr_rows, excel_round_mio
from modules.general_ledger.parser import read_gl_sheet

GL = r"Y:\Seagate\Management Report\2026\0926\GL - MASTER.xlsb"
MR = r"Y:\Seagate\Management Report\2026\0926\Management Report - MASTER harry.xlsb"
pytestmark = pytest.mark.skipif(not (os.path.exists(GL) and os.path.exists(MR)),
                                reason="GL - MASTER.xlsb / Management Report - MASTER harry.xlsb not reachable")


def _norm(text):
    return " ".join(str(text or "").split())


def _coa(v):
    return str(int(v)) if isinstance(v, (int, float)) else ""


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    d = tmp_path_factory.mktemp("mrreal")
    gl, mr = str(d / "gl.xlsb"), str(d / "mr.xlsb")
    shutil.copy(GL, gl)                         # the masters are usually open in Excel
    shutil.copy(MR, mr)
    return gl, mr


@pytest.fixture(scope="module")
def built(files):
    gl, mr = files
    cmap = {(r["source"], r["account"]): (r["coa_ho"], r["category"])
            for r in coa_map.read_coa_sheet(mr)}
    source = {label: read_gl_sheet(gl, sheet).rows
              for label, sheet in (("SMT", "GL SMT"), ("ETF", "GL ETF"))}
    return build_mr_rows(source, cmap)


def ours_key(r):
    return (r["source"], r["coa"], r["mm"], r["cc"], r["category"], _norm(r["description"]), r["act"])


def _combine_rows(mr):
    """Data rows of GL Combine; the trailing helper rows (no Month) are not data and are skipped."""
    out = []
    with open_workbook(mr) as wb, wb.get_sheet("GL Combine") as sh:
        for i, row in enumerate(sh.rows()):
            v = [c.v for c in row] + [None] * 17
            if i == 0 or v[7] not in ("SMT", "ETF") or v[10] is None:
                continue
            out.append((v[7], _coa(v[8]), int(v[10]), str(v[5] or "").strip(), str(v[16] or "").strip(),
                        _norm(v[15]), excel_round_mio(v[6])))
    return out


def test_rows_match_the_gl_combine_sheet(files, built):
    _, mr = files
    theirs_rows = _combine_rows(mr)
    ours_rows = [ours_key(r) for r in built.rows]
    assert built.skipped_date == 0
    assert not [r for r in built.rows if r["unmapped"]]
    # (a) row counts per source
    assert Counter(k[0] for k in ours_rows) == Counter(k[0] for k in theirs_rows)
    # (b) amounts / rounding: identical multiset of (source, month, act), no tolerance
    assert Counter((k[0], k[2], k[6]) for k in ours_rows) == Counter((k[0], k[2], k[6]) for k in theirs_rows)
    # (c) full key. GL Combine contains ~22 manual edits that GL - MASTER does not have (cost centre TFEDUC vs
    # TFKHAR, one category/COA change, one description evaluated from "=R..." text), so allow < 1% difference.
    ours, theirs = Counter(ours_rows), Counter(theirs_rows)
    matched = sum((ours & theirs).values())
    diff = list((ours - theirs).items())[:5] + list((theirs - ours).items())[:5]
    assert matched >= 0.99 * len(ours_rows), (matched, len(ours_rows), diff)


def test_our_act_values_exist_in_append1_with_the_same_rounding(files, built):
    _, mr = files
    acts = {}
    with open_workbook(mr) as wb, wb.get_sheet("Append1") as sh:
        for i, row in enumerate(sh.rows()):
            v = [c.v for c in row] + [None] * 13
            if i == 0 or str(v[9]) != "3":
                continue
            key = (_coa(v[0]), int(v[1]), str(v[3] or "").strip(), str(v[5] or "").strip(), _norm(v[7]))
            acts.setdefault(key, set()).add(round(float(v[11] or 0), 1))
    wrong, absent = [], []
    for r in built.rows:
        key = (r["coa"], r["mm"], r["cc"], r["category"], _norm(r["description"]))
        if key not in acts:
            absent.append((key, r["act"]))        # manual overrides in the MR workbook
        elif r["act"] not in acts[key]:
            wrong.append((key, r["act"], sorted(acts[key])))
    assert not wrong, (len(wrong), wrong[:5])     # rounding rule: zero tolerance
    assert len(absent) <= 0.01 * len(built.rows), (len(absent), absent[:5])
