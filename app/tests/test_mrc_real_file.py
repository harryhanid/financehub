# tests/test_mrc_real_file.py
"""Compares the MR rows we derive with the real workbooks; skipped when they are not reachable."""
import os
import re
import shutil
import sqlite3
from collections import Counter
from datetime import date, timedelta

import pytest
from pyxlsb import open_workbook

from modules.management_report import coa_map, combine_sources
from modules.management_report.combine_rows import build_combine_rows, excel_round_mio
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
    return build_combine_rows(source, cmap, ccmap)


REAL_DB = "C:/Financehub/app/finance_hub.db"


def _real_sponsor_rows():
    """Sponsorship SMT rows from the real dev database, opened read-only (the test DB is isolated)."""
    if not os.path.exists(REAL_DB):
        pytest.skip("real finance_hub.db not reachable")
    conn = sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        smt = conn.execute("SELECT id FROM companies WHERE code='SMT'").fetchone()["id"]
        return [dict(r) for r in conn.execute(
            "SELECT id, tanggal_form_sponsor, perihal, amount_request, coa, cc "
            "FROM sponsorship_transaksi WHERE company_id=?", (smt,))]
    finally:
        conn.close()


def _combine_sponsor_rows(mr_path):
    out = []
    with open_workbook(mr_path) as wb, wb.get_sheet("GL Combine") as sh:
        for i, row in enumerate(sh.rows()):
            v = [c.v for c in row] + [None] * 17
            if i == 0 or v[7] != "Sponsor" or v[10] is None:
                continue
            out.append({"date": (date(1899, 12, 30) + timedelta(days=int(v[2]))).isoformat(),
                        "mm": int(v[10]), "amount": float(v[6]), "memo": _norm(v[3]), "code": v[14]})
    return out


@pytest.fixture(scope="module")
def built_all(files):
    gl, mr = files
    rows, cc_rows = coa_map.read_mapping_sheets(mr)
    cmap = {(r["source"], r["account"]): (r["coa_ho"], r["category"], r["code"]) for r in rows}
    cc_map = {r["cost_center"]: {"total": r["total_cc"], "seq": r["seq"], "description": r["description"]}
              for r in cc_rows}
    source = {label: read_gl_sheet(gl, sheet).rows for label, sheet in (("SMT", "GL SMT"), ("ETF", "GL ETF"))}
    source["Sponsor"] = combine_sources.sponsor_rows_from(_real_sponsor_rows())
    return build_combine_rows(source, cmap, cc_map)


def test_sponsor_rows_match_the_gl_combine_sponsor_rows(files, built_all):
    theirs = _combine_sponsor_rows(files[1])
    ours = [r for r in built_all.rows if r["source"] == "Sponsor" and r["yy"] == 2026 and r["mm"] <= 9]
    assert theirs, "no Sponsor rows read from GL Combine"
    assert len(ours) == len(theirs)                                           # October is not in the workbook yet
    assert Counter(r["mm"] for r in ours) == Counter(t["mm"] for t in theirs)
    # (month, date) is exact; the amount may differ for at most 1 row: Sponsorship was edited after the workbook
    # was made (measured: 1 of 85, "Golf Tournament KADIN", DB 2,898,000 vs workbook 3,000,000).
    assert Counter((r["mm"], r["tgl"]) for r in ours) == Counter((t["mm"], t["date"]) for t in theirs)
    ours_amt = Counter((r["mm"], round(r["debit_credit"]), r["tgl"]) for r in ours)
    theirs_amt = Counter((t["mm"], round(t["amount"]), t["date"]) for t in theirs)
    only_theirs, only_ours = theirs_amt - ours_amt, ours_amt - theirs_amt
    # Pinned exception: the 2026-08-11 Golf Tournament KADIN row. The workbook has 3,000,000, Sponsorship now has
    # 2,898,000 (edited after the workbook was made). Both differences together or neither (if the data is fixed);
    # any other difference fails.
    assert (only_theirs, only_ours) in (
        (Counter(), Counter()),
        (Counter({(8, 3000000, "2026-08-11"): 1}), Counter({(8, 2898000, "2026-08-11"): 1}))),         (dict(only_theirs), dict(only_ours))
    assert {(r["account"], r["coa"], r["cc"], r["cost_center2"], r["cc1"], r["bc1"], r["category"])
            for r in ours} == {("701078002", "701078002", "POSPON", "$POCCOM", 5, "", "")}
    memo_hits = sum((Counter(_norm(r["allocation_memo"]) for r in ours) & Counter(t["memo"] for t in theirs)).values())
    assert memo_hits >= 0.95 * len(theirs)                                    # 83/85 measured; the rest are manual edits
    ours_codes = [r["new_code"] for r in ours]
    theirs_codes = [t["code"] for t in theirs]
    assert sorted(ours_codes) == sorted(theirs_codes)                         # A26-51 .. A26-5<n>, as a set
    same_position = sum(a == b for a, b in zip(ours_codes, theirs_codes)) / len(theirs_codes)
    assert same_position >= 0.95                                              # 1.0 measured (85/85 same position)


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


def test_our_act_values_exist_in_append1_with_the_same_rounding(files, built_all):
    _, mr = files
    acts = {}
    with open_workbook(mr) as wb, wb.get_sheet("Append1") as sh:
        for i, row in enumerate(sh.rows()):
            v = [c.v for c in row] + [None] * 13
            if i == 0 or str(v[9]) != "3":
                continue
            key = (_coa(v[0]), int(v[1]), str(v[3] or "").strip(), str(v[5] or "").strip(), _norm(v[7]))
            acts.setdefault(key, set()).add(round(float(v[11] or 0), 1))
    # Append1 holds 2026 only and its key has no year, so earlier Sponsorship years (2018-2025) must be left out
    rows26 = [r for r in built_all.rows if r["yy"] == 2026]
    wrong, absent = [], []
    for r in rows26:
        key = (r["coa"], r["mm"], r["cc"], r["category"], _norm(r["description"]))
        if key not in acts:
            absent.append((key, r["act"]))        # manual overrides in the MR workbook
        elif r["act"] not in acts[key]:
            wrong.append((key, r["act"], sorted(acts[key])))
    # rounding rule: zero tolerance for GL rows. The one Sponsor row whose amount was edited in Sponsorship after
    # the workbook was made (DB 2,898,000 vs workbook 3,000,000) is the only allowed deviation, Sponsor only.
    wrong_gl = [w for w in wrong if w[0][2] != "POSPON"]
    wrong_sp = [w for w in wrong if w[0][2] == "POSPON"]
    assert not wrong_gl, (len(wrong_gl), wrong_gl[:5])
    # Pinned exception: the Golf Tournament KADIN row (ours 2.9, Append1 3.0); zero mismatches also passes.
    assert all("Golf Tournament KADIN" in w[0][4] and w[1] == 2.9 and w[2] == [3.0] for w in wrong_sp)         and len(wrong_sp) <= 1, wrong_sp
    assert len(absent) <= 0.01 * len(rows26), (len(absent), absent[:5])


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
