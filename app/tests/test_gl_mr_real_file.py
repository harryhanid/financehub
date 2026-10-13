# tests/test_gl_mr_real_file.py
"""Compares the MR rows we derive with the real workbooks; skipped when they are not reachable."""
import os
import re
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
    coa_rows, cc_rows = coa_map.read_mapping_sheets(mr)
    cmap = {(r["source"], r["account"]): (r["coa_ho"], r["category"], r["code"]) for r in coa_rows}
    ccmap = {r["cost_center"]: {"total": r["total_cc"], "seq": r["seq"], "description": r["description"]}
             for r in cc_rows}
    source = {label: read_gl_sheet(gl, sheet).rows
              for label, sheet in (("SMT", "GL SMT"), ("ETF", "GL ETF"))}
    return build_mr_rows(source, cmap, ccmap)


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


def _combine_full(mr):
    """GL Combine rows (SMT/ETF with a Month) as raw value lists, in sheet order."""
    out = []
    with open_workbook(mr) as wb, wb.get_sheet("GL Combine") as sh:
        for i, row in enumerate(sh.rows()):
            v = [c.v for c in row] + [None] * 17
            if i == 0 or v[7] not in ("SMT", "ETF") or v[10] is None:
                continue
            out.append(v)
    return out


def _empty(x):
    """Excel shows a missing lookup as 0 or blank; treat 0 / None / '' alike."""
    if x is None or x == 0 or str(x).strip() == "":
        return ""
    return x if isinstance(x, str) else int(x)


def test_new_columns_match_gl_combine(files, built):
    """Row by row (same order) cost_center2, cc1, bc1 and new_code against GL Combine cols 9, 12, 13, 14.

    Measured on the real workbook (5395 rows): bc1 1 mismatch (row 5120, a manual COA re-class: COA HO differs
    too); cost_center2 22 mismatches = 2 PULPP rows (Combine 0, ours "") is handled as equal, plus 20 rows where
    the Combine hand-edited COST CENTER (TFEDUC -> TFKHAR); cc1 20 mismatches, the same 20 rows; new_code 250
    mismatches (4.63%), ALL inside the 6 (cc0, cc1, bc1) groups touched by the 21 hand-edited rows (a changed
    cost centre / category shifts the running numbers in the old and the new group).
    Threshold: new_code <= 300 mismatches (5.6%, about 20% headroom over the 250 measured) AND every mismatching
    row must lie in a touched group - so an unrelated numbering bug fails even when under the threshold.
    """
    _, mr = files
    theirs = _combine_full(mr)
    assert len(theirs) == len(built.rows)
    edited = [k for k, (o, t) in enumerate(zip(built.rows, theirs))
              if o["cc"] != str(t[5] or "").strip() or o["bc1"] != str(t[13] or "").strip()]
    assert len(edited) <= 25, len(edited)                 # known hand edits: 21 measured

    # bc1: exact, except hand re-classed rows (COA HO differs from ours)
    bc_bad = [(k, built.rows[k]["bc1"], theirs[k][13]) for k, (o, t) in enumerate(zip(built.rows, theirs))
              if o["bc1"] != str(t[13] or "").strip()]
    assert all(_coa(theirs[k][8]) != built.rows[k]["coa"] for k, *_ in bc_bad), bc_bad[:5]
    assert len(bc_bad) <= 2, bc_bad[:5]

    # cost_center2 / cc1: exact except rows whose cost centre was hand-edited in Combine
    edited_set = set(edited)
    cc2_bad = [(k, built.rows[k]["cc"], built.rows[k]["cost_center2"], theirs[k][5], theirs[k][9])
               for k, (o, t) in enumerate(zip(built.rows, theirs))
               if _empty(o["cost_center2"]) != _empty(t[9] if not isinstance(t[9], str) else t[9].strip())
               and k not in edited_set]
    cc1_bad = [(k, built.rows[k]["cc"], built.rows[k]["cc1"], theirs[k][5], theirs[k][12])
               for k, (o, t) in enumerate(zip(built.rows, theirs))
               if _empty(o["cc1"]) != _empty(t[12]) and k not in edited_set]
    assert not cc2_bad, (len(cc2_bad), cc2_bad[:5])
    assert not cc1_bad, (len(cc1_bad), cc1_bad[:5])
    pulpp = [k for k, o in enumerate(built.rows) if o["cc"] == "PULPP"]
    assert len(pulpp) == 2 and all(built.rows[k]["cc_unmapped"] and built.rows[k]["cc1"] == 0 for k in pulpp)

    # new_code
    nc_bad = [(k, o["new_code"], str(t[14]).strip(), o["cc"], t[5]) for k, (o, t) in enumerate(zip(built.rows, theirs))
              if o["new_code"] != str(t[14]).strip()]
    touched = set()
    for k in edited:
        touched.add(f"A{built.rows[k]['cc0']}-{built.rows[k]['cc1']}{built.rows[k]['bc1']}")
        touched.add(re.sub(r"\d+$", "", str(theirs[k][14])))
    outside = [x for x in nc_bad
               if re.sub(r"\d+$", "", x[1]) not in touched and re.sub(r"\d+$", "", x[2]) not in touched]
    assert not outside, (len(outside), outside[:5])
    assert len(nc_bad) <= 300, (len(nc_bad), nc_bad[:5])
