# Management Report export: reference format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sheet 1 and sheet 2 of the per-CC Management Report export look and are structured like `Report YTD Aug 2025 - POCPRO.xlsx` ("BGT Report per CC", "BGT HO Report per CC").

**Architecture:** A pure builder (`bgt_report.py`) turns Append rows into the OPEX/CAPEX -> category -> detail structure with full-year and YTD amounts; a writer (`bgt_exports.py`) draws it with openpyxl using the reference styles; `exports.build_cc_workbook` gets an optional `bgt` argument (old callers keep working); `ho_exports.py` is restyled in place; routes build and pass the new data.

**Tech Stack:** Flask, SQLite, openpyxl, pytest (code lives in `C:\Financehub\app`, tests run from that folder).

Spec: `docs/superpowers/specs/2026-10-06-mr-export-reference-format-design.md` (see "Adjustments agreed while planning" at the end of the spec; they override the spec body where they differ).

## Global Constraints

- **Do NOT run `git add`, `git commit`, `git stash` or `git checkout` for code files.** `C:\Financehub` is the user's live tree with uncommitted work. Edit files with the Edit/Write tools only. Never kill or restart processes on port 8081.
- New function parameters are optional so existing callers and tests keep working.
- Files use CRLF line endings in several places: before editing a file check it (`grep -c $'\r$' file`) and keep its ending style; append test code with the same ending as the file.
- Amounts are numbers (no formulas), in Rp Mio on sheet 1 and Rp 000 on sheet 2 (as today).
- Sheet names: `BGT Report per CC`, `BGT HO Report per CC`, `Append`. When `build_cc_workbook` is called without `bgt` (legacy callers) its first sheet stays the old `Report`.
- Reference colours: header blue `538DD5`; OPEX/CAPEX row `95B3D7`; category row `CCECFF`; name cells `F6C6AD`; period cells `C1E4F5`; HO header `FFCC99`; HO amount cells `CCFFFF`; HO date/code cells `7CEB99`; italic/negative rules unchanged.
- Month used for YTD of a line = `mm1`, falling back to `mm`; a line with no month counts as within YTD.
- Run the affected tests with `python -m pytest <files> -q` from `C:\Financehub\app`.

## File Structure

- Create `app/modules/management_report/bgt_report.py` - pure data builder (Task 1).
- Create `app/modules/management_report/bgt_exports.py` - sheet 1 writer (Task 2).
- Modify `app/modules/management_report/exports.py` - optional `bgt` argument in `build_cc_workbook` / `bgt_by_cc` in `build_zip` (Task 2).
- Modify `app/modules/management_report/ho_exports.py`, `ho_report.py` - restyle sheet 2, rename, add `period` key (Task 3).
- Modify `app/modules/management_report/routes.py` - build and pass `bgt` (Task 4).
- Tests: create `app/tests/test_mr_bgt_report.py`, `app/tests/test_mr_bgt_exports.py`; adjust `app/tests/test_mr_exports.py`, `app/tests/test_mr_routes.py` sheet names.

---

### Task 1: Builder `bgt_report.py`

**Files:**
- Create: `app/modules/management_report/bgt_report.py`
- Test: `app/tests/test_mr_bgt_report.py`

**Interfaces:**
- Produces: `build_bgt_report(rows, yy=None, mm=None, meta_period=None) -> dict` with keys `has_data, year, year4, period, period_date, levels`; `levels` = `[{"label": "OPEX"|"CAPEX", "m": metrics, "categories": [{"label", "m", "details": [{"coa","text","d","e","f","i"}]}]}]`; `metrics` = dict with keys `d,e,f,g,i,j,k,m,n` (`k`/`n` are `None` when the divisor is 0).
- Consumes: Append row dicts (keys `coa, mm, yy, cc, category, activity, description, pta, custom, mm1, act, bgt`), already filtered by cc/yy/coa but NOT by month.

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_mr_bgt_report.py`:

```python
from datetime import date

import pytest

from modules.management_report.bgt_report import (build_bgt_report, clean_category, month_of,
                                                   pick_period)


def row(coa, category, description, mm1, bgt=0.0, pta=0.0, act=0.0, yy=26, mm=None):
    return dict(coa=coa, mm=mm if mm is not None else mm1, yy=yy, cc="AAA", category=category,
                activity="Operational", description=description, pta=pta, custom="1",
                mm1=mm1, act=act, bgt=bgt)


ROWS = [
    row("70105120", "01 - Rental, Tax", "Rent", 1, bgt=10, act=4),
    row("70105120", "01 - Rental, Tax", "Rent", 9, bgt=6),
    row("70106100", "02 - Transport", "Taxi", 2, bgt=3, pta=1),
    row("27004100", "21 - Office Furniture & Fixture", "Chair", 2, bgt=5, pta=2),
]


def test_clean_category_drops_the_number_prefix():
    assert clean_category("01 - Rental, Tax & License Expense") == "Rental, Tax & License Expense"
    assert clean_category("Plain") == "Plain"
    assert clean_category(None) == "(no category)"


def test_month_of_prefers_mm1_then_mm():
    assert month_of({"mm1": 4, "mm": 5}) == 4
    assert month_of({"mm1": None, "mm": 5}) == 5
    assert month_of({"mm1": 0, "mm": None}) is None


def test_period_priority_mm_then_meta_then_latest_act_then_12():
    assert pick_period(ROWS, 26, 8, "2026-03-31") == 8
    assert pick_period(ROWS, 26, None, "2026-03-31") == 3
    assert pick_period(ROWS, 26, None, "2025-03-31") == 1          # meta year differs -> latest month with ACT
    assert pick_period(ROWS, 26, None, None) == 1
    assert pick_period([row("1", "c", "d", 2, bgt=1)], 26, None, None) == 12


def test_structure_levels_categories_and_details():
    rep = build_bgt_report(ROWS, None, 8)
    assert rep["has_data"] and rep["year"] == 26 and rep["year4"] == 2026 and rep["period"] == 8
    assert rep["period_date"] == date(2026, 8, 31)
    assert [l["label"] for l in rep["levels"]] == ["OPEX", "CAPEX"]
    opex, capex = rep["levels"]
    assert [c["label"] for c in opex["categories"]] == ["Rental, Tax", "Transport"]
    assert [c["label"] for c in capex["categories"]] == ["Office Furniture & Fixture"]
    rental = opex["categories"][0]
    assert [d["text"] for d in rental["details"]] == [
        "- Bgt 2026 : Rent Month : 1", "- Bgt 2026 : Rent Month : 9", "- Act 2026 : Rent Month : 1"]
    d1, d9, a1 = rental["details"]
    assert (d1["coa"], d1["d"], d1["e"], d1["f"], d1["i"]) == ("70105120", 10, 10, None, None)
    assert (d9["d"], d9["e"]) == (6, 0)                              # month 9 is after the period
    assert (a1["d"], a1["e"], a1["f"], a1["i"]) == (None, None, None, 4)


def test_metrics_full_year_ytd_and_percentages():
    rep = build_bgt_report(ROWS, None, 8)
    m = rep["levels"][0]["m"]
    assert (m["d"], m["e"], m["f"], m["g"], m["i"]) == (19, 13, 1, 14, 4)
    assert m["j"] == -10 and m["k"] == pytest.approx(-10 / 14)
    assert m["m"] == 15 and m["n"] == pytest.approx(15 / 19)
    cat = rep["levels"][0]["categories"][0]["m"]
    assert (cat["d"], cat["e"], cat["f"], cat["i"]) == (16, 10, 0, 4)
    capex = rep["levels"][1]["m"]
    assert (capex["d"], capex["e"], capex["f"], capex["g"], capex["i"], capex["j"], capex["m"]) == (5, 5, 2, 7, 0, -7, 5)


def test_zero_divisors_give_none():
    rep = build_bgt_report([row("70105120", "01 - A", "x", 1, act=3)], None, 1)
    m = rep["levels"][0]["m"]
    assert m["d"] == 0 and m["g"] == 0 and m["k"] is None and m["n"] is None


def test_other_years_are_ignored_and_default_year_is_latest():
    rows = ROWS + [row("70105120", "01 - Rental, Tax", "Old", 1, bgt=99, yy=25)]
    rep = build_bgt_report(rows, None, 8)
    assert rep["year"] == 26 and rep["levels"][0]["m"]["d"] == 19
    assert build_bgt_report(rows, 25, 8)["levels"][0]["m"]["d"] == 99


def test_empty_rows_give_no_levels():
    rep = build_bgt_report([], None, None)
    assert rep["has_data"] is False and rep["levels"] == [] and rep["period"] is None
    assert rep["period_date"] is None and rep["year"] is None
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_bgt_report.py -q`
Expected: FAIL (ImportError: no module `bgt_report`).

- [ ] **Step 3: Implement**

Create `app/modules/management_report/bgt_report.py`:

```python
"""Management Report: data of sheet 'BGT Report per CC' (OPEX/CAPEX -> category -> Append lines)."""
import calendar
import re
from datetime import date

_PREFIX = re.compile(r"^\s*\d+\s*-\s*")
_KINDS = (("Bgt", "bgt", "d"), ("Pta", "pta", "f"), ("Act", "act", "i"))


def clean_category(name) -> str:
    return _PREFIX.sub("", name or "").strip() or "(no category)"


def month_of(row):
    return row.get("mm1") or row.get("mm") or None


def _full_year(yy):
    if yy is None:
        return None
    return yy + 2000 if yy < 100 else yy


def pick_year(rows, yy):
    if yy is not None:
        return yy
    years = [r["yy"] for r in rows if r.get("yy") is not None]
    return max(years) if years else None


def pick_period(rows, year, mm, meta_period) -> int:
    """mm filter, else the snapshot's report period (same year), else the latest month with ACT, else 12."""
    if mm is not None:
        return int(mm)
    if meta_period and year is not None:
        try:
            y, m = int(str(meta_period)[:4]), int(str(meta_period)[5:7])
        except ValueError:
            y = m = 0
        if y == _full_year(year) and 1 <= m <= 12:
            return m
    months = [month_of(r) for r in rows
              if r.get("yy") == year and (r.get("act") or 0) != 0 and month_of(r)]
    return max(months) if months else 12


def _metrics(d, e, f, i) -> dict:
    g = e + f
    j = i - g
    m = d - i
    return {"d": d, "e": e, "f": f, "g": g, "i": i, "j": j,
            "k": j / g if g else None, "m": m, "n": m / d if d else None}


def _sum(items) -> dict:
    t = {k: 0.0 for k in "defi"}
    for it in items:
        for k in t:
            t[k] += it[k] or 0
    return _metrics(t["d"], t["e"], t["f"], t["i"])


def _details(rows, year4, period):
    out = []
    for kind_no, (kind, field, col) in enumerate(_KINDS):
        for r in sorted(rows, key=lambda r: (str(r.get("coa") or ""), month_of(r) or 0,
                                             (r.get("description") or "").lower())):
            amount = r.get(field) or 0
            if amount == 0:
                continue
            month = month_of(r)
            within = month is None or month <= period
            text = f"- {kind} {year4 or ''} : {r.get('description') or ''}"
            if r.get("mm1"):
                text += f" Month : {r['mm1']}"
            d = {"coa": r.get("coa"), "text": text, "d": None, "e": None, "f": None, "i": None}
            d[col] = amount if (col == "d" or within) else 0.0
            if col == "d":
                d["e"] = amount if within else 0.0
            out.append((kind_no, d))
    return [d for _, d in out]


def build_bgt_report(rows, yy=None, mm=None, meta_period=None) -> dict:
    empty = {"has_data": False, "year": None, "year4": None, "period": None,
             "period_date": None, "levels": []}
    year = pick_year(rows, yy)
    rows = [r for r in rows if year is None or r.get("yy") == year]
    if not rows:
        return empty
    period = pick_period(rows, year, mm, meta_period)
    year4 = _full_year(year)

    by_level = {"OPEX": {}, "CAPEX": {}}
    for r in sorted(rows, key=lambda r: str(r.get("category") or "").lower()):
        level = "CAPEX" if str(r.get("coa") or "").startswith("27") else "OPEX"
        by_level[level].setdefault(r.get("category"), []).append(r)

    levels = []
    for label in ("OPEX", "CAPEX"):
        cats = []
        for category, cat_rows in by_level[label].items():
            details = _details(cat_rows, year4, period)
            cats.append({"label": clean_category(category), "m": _sum(details), "details": details})
        if cats:
            levels.append({"label": label, "m": _sum(c["m"] for c in cats), "categories": cats})
    last_day = calendar.monthrange(year4, period)[1] if year4 else None
    return {"has_data": True, "year": year, "year4": year4, "period": period,
            "period_date": date(year4, period, last_day) if year4 else None, "levels": levels}
```

Note for the implementer: `_sum(c["m"] for c in cats)` receives metric dicts (keys `d,e,f,i` exist in them), so level totals equal the sum of categories. If a test shows the Bgt/Pta/Act kind ordering differs from the expected list in `test_structure_levels_categories_and_details`, fix the code, not the test (Bgt lines first, then Pta, then Act, each sorted by COA, month, description).

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_mr_bgt_report.py -q`
Expected: all pass.

- [ ] **Step 5: Report (no commit)** - state the files touched and the test result.

---

### Task 2: Sheet 1 writer and workbook wiring

**Files:**
- Create: `app/modules/management_report/bgt_exports.py`
- Modify: `app/modules/management_report/exports.py` (`build_cc_workbook`, `build_zip`)
- Test: `app/tests/test_mr_bgt_exports.py`

**Interfaces:**
- Consumes: Task 1 `build_bgt_report` output, extended by the caller with `title, cc_code, cc_desc, company_code`.
- Produces: `write_bgt_sheet(ws, bgt)`; `build_cc_workbook(report, filters=None, ho=None, append_rows=None, bgt=None)`; `build_zip(reports, filters=None, ho_by_cc=None, append_by_cc=None, bgt_by_cc=None)`.

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_mr_bgt_exports.py`:

```python
import io
from datetime import datetime

from openpyxl import load_workbook

from modules.management_report.bgt_report import build_bgt_report
from modules.management_report.exports import build_cc_workbook, build_zip
from tests.test_mr_bgt_report import ROWS

REPORT = {"cc": "AAA", "has_data": True, "groups": [], "grand": {}, "title": "unused"}


def _bgt(rows=ROWS, mm=8):
    bgt = build_bgt_report(rows, None, mm)
    bgt.update(title="President Office & ETF – Alpha Unit", cc_code="AAA",
               cc_desc="Alpha Unit", company_code="ETF")
    return bgt


def _ws(rows=ROWS, mm=8):
    wb = load_workbook(io.BytesIO(build_cc_workbook(REPORT, {}, None, None, _bgt(rows, mm))))
    assert wb.sheetnames == ["BGT Report per CC"]
    return wb["BGT Report per CC"]


def _fill(c):
    return c.fill.fgColor.rgb[-6:]


def test_header_block():
    ws = _ws()
    assert ws["C1"].value == "President Office & ETF – Alpha Unit" and ws["C2"].value == "In Rp Mio"
    assert ws["A2"].value == "AAA" and ws["A3"].value == "ETF - Alpha Unit"
    assert ws["C4"].value == "Period:" and ws["D4"].value == datetime(2026, 8, 31)
    assert ws["D4"].number_format == "mmm-yy"
    merged = {str(r) for r in ws.merged_cells.ranges}
    assert {"C1:O1", "C2:O2", "C6:C8", "D6:G6", "I6:K6", "M6:N7", "O6:O8", "J7:K7"} <= merged
    assert ws["C6"].value == "Description" and ws["D6"].value == "Consolidation Budget"
    assert ws["I6"].value == "Consolidation Actual" and ws["O6"].value == "Remarks"
    assert ws["M6"].value == "Available Bgt YTD 2026 - Actual Aug 2026"
    assert ws["J7"].value == "Var A Aug 2026 to B Aug 2026"
    assert ws["G5"].value == "4\n( 2 + 3 )" and ws["K5"].value == "( 5 - 4 ) / 4"
    assert ws["E8"].value == datetime(2026, 8, 31) and ws["J8"].value == "Amount" and ws["K8"].value == "%"
    assert _fill(ws["C6"]) == "538DD5" and ws["C6"].font.color.rgb[-6:] == "FFFFFF"
    assert ws.sheet_view.zoomScale == 70
    assert ws.column_dimensions["C"].width == 59.3 and ws.column_dimensions["H"].width == 1.4


def test_body_rows_and_values():
    ws = _ws()
    assert ws["C10"].value == "OPEX" and _fill(ws["C10"]) == "95B3D7"
    assert [ws[f"{c}10"].value for c in "DEFGIJ"] == [19, 13, 1, 14, 4, -10]
    assert ws["K10"].value == -10 / 14 and ws["K10"].number_format == "0.0%"
    assert ws["M10"].value == 15 and ws["N10"].value == 15 / 19
    assert ws["C11"].value == "Rental, Tax" and _fill(ws["C11"]) == "CCECFF" and ws["C11"].font.bold
    assert ws["D11"].value == 16 and ws["I11"].value == 4
    assert ws["B12"].value == 70105120 and ws["C12"].value == "- Bgt 2026 : Rent Month : 1"
    assert (ws["D12"].value, ws["E12"].value, ws["F12"].value) == (10, 10, None)
    assert ws["C14"].value == "- Act 2026 : Rent Month : 1" and ws["I14"].value == 4
    assert ws["C18"].value == "CAPEX" and ws["C19"].value == "Office Furniture & Fixture"


def test_details_are_grouped_and_hidden_headers_are_not():
    ws = _ws()
    for r in (12, 13, 14, 16, 17, 20, 21):
        dim = ws.row_dimensions[r]
        assert dim.hidden and dim.outlineLevel == 2, r
    for r in (10, 11, 15, 18, 19):
        assert not ws.row_dimensions[r].hidden and not ws.row_dimensions[r].outlineLevel, r
    assert ws.sheet_properties.outlinePr.summaryBelow is False


def test_no_data_writes_only_the_header():
    wb = load_workbook(io.BytesIO(build_cc_workbook(
        REPORT, {}, None, None, {**_bgt([]), "has_data": False})))
    ws = wb["BGT Report per CC"]
    assert ws["C6"].value == "Description" and ws["C10"].value is None
    assert ws["D4"].value is None


def test_text_starting_with_equals_stays_text():
    rows = [dict(ROWS[0], category="01 - =SUM(1)", description="=cmd")]
    ws = _ws(rows)
    assert ws["C11"].value == "=SUM(1)" and ws["C11"].data_type == "s"
    assert ws["C12"].data_type == "s"


def test_legacy_call_keeps_the_old_report_sheet():
    wb = load_workbook(io.BytesIO(build_cc_workbook(REPORT)))
    assert wb.sheetnames == ["Report"]


def test_zip_uses_the_new_sheet_per_cc():
    import zipfile
    data = build_zip([REPORT], {}, None, None, {"AAA": _bgt()})
    zf = zipfile.ZipFile(io.BytesIO(data))
    assert load_workbook(io.BytesIO(zf.read("AAA.xlsx"))).sheetnames == ["BGT Report per CC"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_bgt_exports.py -q`
Expected: FAIL (TypeError: unexpected `bgt` argument / ImportError).

- [ ] **Step 3: Implement the writer**

Create `app/modules/management_report/bgt_exports.py`:

```python
"""Sheet 'BGT Report per CC' of the per-CC export, in the layout of the reference workbook."""
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.properties import Outline

_FONT = "Aptos Narrow"
_BLUE = PatternFill("solid", fgColor="538DD5")
_LEVEL = PatternFill("solid", fgColor="95B3D7")
_CATEGORY = PatternFill("solid", fgColor="CCECFF")
_NAME = PatternFill("solid", fgColor="F6C6AD")
_PERIOD = PatternFill("solid", fgColor="C1E4F5")
_NUM = '_(* #,##0_);_(* \\(#,##0\\);_(* "-"??_);_(@_)'
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_WIDTHS = {"A": 8.4, "B": 11.7, "C": 59.3, "D": 11.5, "E": 10.9, "F": 12.8, "G": 19.9, "H": 1.4,
           "I": 11.4, "J": 10.8, "K": 11.7, "L": 1.3, "M": 11.2, "N": 11.7, "O": 16}
_METRICS = (("d", "D"), ("e", "E"), ("f", "F"), ("g", "G"), ("i", "I"),
            ("j", "J"), ("k", "K"), ("m", "M"), ("n", "N"))
_FIRST_ROW = 10
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _font(size=11, bold=False, color=None):
    return Font(name=_FONT, size=size, bold=bold, color=color)


def _text(cell, value):
    """Plain text: a value that starts with '=' must not become a formula."""
    cell.value = value
    if isinstance(value, str):
        cell.data_type = "s"


def _header(ws, bgt):
    period, year4 = bgt.get("period"), bgt.get("year4")
    mon = f"{_MONTHS[period - 1]} {year4}" if period and year4 else ""
    pdate = bgt.get("period_date")

    for r, h in ((1, 26), (2, 26), (3, 26), (4, 16), (5, 32), (6, 16), (7, 43.5), (8, 16)):
        ws.row_dimensions[r].height = h
    ws.merge_cells("C1:O1")
    ws.merge_cells("C2:O2")
    for ref, value in (("C1", bgt.get("title")), ("C2", "In Rp Mio")):
        _text(ws[ref], value)
        ws[ref].font = _font(20, True)
        ws[ref].alignment = Alignment(horizontal="center", vertical="center")
    for ref, value in (("A2", bgt.get("cc_code")),
                       ("A3", f"{bgt.get('company_code')} - {bgt.get('cc_desc')}")):
        _text(ws[ref], value)
    for ref in ("A2", "B2", "A3", "B3"):
        ws[ref].font = _font(11, True)
        ws[ref].fill = _NAME

    ws["C4"], ws["D4"] = "Period:", pdate
    for ref in ("C4", "D4"):
        ws[ref].font = _font(12, True)
        ws[ref].fill = _PERIOD
    ws["C4"].alignment = Alignment(horizontal="left")
    ws["D4"].alignment = Alignment(horizontal="center")
    ws["D4"].number_format = "mmm-yy"

    for ref, value in (("D5", 1), ("E5", 2), ("F5", 3), ("G5", "4\n( 2 + 3 )"), ("I5", 5),
                       ("J5", "( 5 - 4 )"), ("K5", "( 5 - 4 ) / 4"), ("M5", "( 1 - 5 )"),
                       ("N5", "( 1 - 5 ) / 1")):
        ws[ref] = value
        ws[ref].font = _font(12, True)
        ws[ref].alignment = _CENTER

    for col in "CDEFGIJKMNO":
        for r in (6, 7, 8):
            c = ws[f"{col}{r}"]
            c.fill, c.font, c.alignment = _BLUE, _font(11, True, "FFFFFF"), _CENTER
    labels = {"C6": "Description", "D6": "Consolidation Budget", "I6": "Consolidation Actual",
              "M6": f"Available Bgt YTD {year4 or ''} - Actual {mon}", "O6": "Remarks",
              "D7": "Budget Full Year", "E7": "Budget YTD", "F7": "PTA YTD",
              "G7": "Budget Available YTD\n(Budget + PTA)", "I7": "Actual YTD",
              "J7": f"Var A {mon} to B {mon}", "J8": "Amount", "K8": "%", "M8": "Amount", "N8": "%"}
    for ref, value in labels.items():
        ws[ref] = value
    for col in "EFGI":
        ws[f"{col}8"] = pdate
        ws[f"{col}8"].number_format = "mmm-yy"
    for rng in ("C6:C8", "D6:G6", "I6:K6", "M6:N7", "O6:O8", "J7:K7"):
        ws.merge_cells(rng)


def _level_row(ws, r, label, m, fill, pct_format):
    for col in "CDEFGIJKMNO":
        ws[f"{col}{r}"].fill = fill
        ws[f"{col}{r}"].font = _font(11, True)
    _text(ws[f"C{r}"], label)
    for key, col in _METRICS:
        c = ws[f"{col}{r}"]
        c.value = m[key]
        c.number_format = pct_format if key in ("k", "n") else _NUM


def _detail_row(ws, r, d):
    coa = d["coa"]
    b = ws.cell(r, 2)
    b.value = int(coa) if str(coa).isdigit() else coa
    b.font = _font()
    c = ws.cell(r, 3)
    _text(c, d["text"])
    c.font = _font()
    for key, col in (("d", "D"), ("e", "E"), ("f", "F"), ("i", "I")):
        if d[key] is not None:
            cell = ws[f"{col}{r}"]
            cell.value = d[key]
            cell.number_format = _NUM
            cell.font = _font()
    dim = ws.row_dimensions[r]
    dim.outlineLevel = 2
    dim.hidden = True


def write_bgt_sheet(ws, bgt: dict) -> None:
    ws.sheet_view.zoomScale = 70
    ws.sheet_properties.outlinePr = Outline(summaryBelow=False, summaryRight=True)
    for col, width in _WIDTHS.items():
        ws.column_dimensions[col].width = width
    _header(ws, bgt)
    r = _FIRST_ROW
    for level in bgt.get("levels", []):
        _level_row(ws, r, level["label"], level["m"], _LEVEL, "0.0%")
        r += 1
        for cat in level["categories"]:
            _level_row(ws, r, cat["label"], cat["m"], _CATEGORY, "0%")
            r += 1
            for d in cat["details"]:
                _detail_row(ws, r, d)
                r += 1
```

- [ ] **Step 4: Wire into `exports.py`**

In `app/modules/management_report/exports.py`:
1. Add `from modules.management_report import bgt_exports, ho_exports` (replace the existing `ho_exports` import line).
2. Change the `build_cc_workbook` signature to `def build_cc_workbook(report: dict, filters: dict = None, ho: dict = None, append_rows: list = None, bgt: dict = None) -> bytes:`.
3. Right after `ws.title = "Report"` insert: when `bgt is not None`, set `ws.title = "BGT Report per CC"`, call `bgt_exports.write_bgt_sheet(ws, bgt)`, and skip the legacy block; the legacy block (everything from `ws["A1"] = ...` through `ws.freeze_panes = ...`) must run only when `bgt is None`. Implement as `if bgt is not None: ... else: <existing legacy code unchanged>` by moving the legacy lines into a private helper `_write_legacy_report(ws, report, filters)` and calling it in the `else` branch. The code after it (HO sheet, Append sheet, save) stays shared.
4. Change `build_zip` to `def build_zip(reports, filters=None, ho_by_cc=None, append_by_cc=None, bgt_by_cc=None)` and pass `(bgt_by_cc or {}).get(rep["cc"])` as the new last argument to `build_cc_workbook`.

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_mr_bgt_exports.py tests/test_mr_bgt_report.py -q`
Expected: pass. Also run `python -m pytest tests/test_mr_exports.py -q`: legacy tests must still pass (HO sheet name tests are handled in Task 3).

- [ ] **Step 6: Report (no commit).**

---

### Task 3: HO sheet restyle ("BGT HO Report per CC")

**Files:**
- Modify: `app/modules/management_report/ho_exports.py`, `app/modules/management_report/ho_report.py`
- Test: `app/tests/test_mr_exports.py` (HO tests)

**Interfaces:**
- Produces: sheet named `BGT HO Report per CC`; `build_ho_report(...)` result gains `"period": meta.get("period")` (ISO string or None).

- [ ] **Step 1: Write the failing tests**

Append to `app/tests/test_mr_exports.py` (use the existing `ho_seeded` fixture and `_ho_workbook`, `_row_with` helpers; preserve the file's line endings):

```python
def test_ho_sheet_is_named_like_the_master_and_styled_like_the_reference(ho_seeded):
    wb = _ho_workbook()
    assert wb.sheetnames == ["Report", "BGT HO Report per CC"]
    ws = wb["BGT HO Report per CC"]
    assert ws["G2"].value.year == 2026 and ws["G2"].value.month == 8
    assert ws["G2"].fill.fgColor.rgb[-6:] == "7CEB99" and ws["G3"].value == "AAA"
    assert ws["G3"].fill.fgColor.rgb[-6:] == "7CEB99"
    head = _row_with(ws, "GL Account", 1)
    assert ws.cell(head, 1).fill.fgColor.rgb[-6:] == "FFCC99"
    assert ws.cell(head, 1).border.left.style == "medium" and ws.cell(head, 1).border.top.style == "medium"
    assert ws.cell(head + 1, 4).border.bottom.style == "medium"
    r = _row_with(ws, 70105120, 1)
    assert ws.cell(r, 4).fill.fgColor.rgb[-6:] == "CCFFFF"
    assert ws.cell(r, 4).border.left.style == "medium" and ws.cell(r, 4).border.right.style == "medium"
    assert ws.cell(r, 1).border.left.style == "medium" and ws.cell(r, 1).border.right.style == "thin"
    t = _row_with(ws, "Total - 701-05-xxx", 1)
    assert ws.cell(t, 1).border.top.style == "thin" and ws.cell(t, 4).border.bottom.style == "thin"
    assert ws.cell(t, 1).alignment.horizontal == "centerContinuous"
    g = _row_with(ws, "Grand Total included Depreciation", 1)
    assert ws.cell(g, 4).border.top.style == "medium"
    assert ws.column_dimensions["A"].width == 17.2 and ws.column_dimensions["B"].width == 52
```

Also in the same file replace the old sheet name `"HO Report"` with `"BGT HO Report per CC"` everywhere it is used as a sheet name (`wb["HO Report"]`, `wb.sheetnames == [...]`, `_ho_workbook()["HO Report"]`), and in `tests/test_mr_routes.py` line ~387 (`["Report", "HO Report", "Append"]`) - routes keep returning the new first sheet name only after Task 4, so for now change only the HO name in that list.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_exports.py -q`
Expected: FAIL (sheet name, fills, borders).

- [ ] **Step 3: Implement**

In `ho_report.py` `build_ho_report`, add `"period": meta.get("period"),` to the `out.update({...})` dict.

In `ho_exports.py`:
1. Imports: `from datetime import date`, and keep `Alignment, Border, Font, PatternFill, Side`.
2. Constants: `_HEAD = PatternFill("solid", fgColor="FFCC99")`, `_GREEN = PatternFill("solid", fgColor="7CEB99")`, replace `_LINE` by `_MED = Side(style="medium")` and `_THIN = Side(style="thin")`, widths `{"A": 17.2, "B": 52, "C": 8.5, "D": 16, "E": 14, "F": 16, "G": 30}`.
3. Add the frame helper:

```python
def _frame(ws, r, summary, top=None, bottom=None):
    """Reference borders: medium frame at the sides of the table, thin inside the summary section."""
    inner = _THIN if summary else _MED
    for col in range(1, 7):
        left = _MED if col == 1 else (inner if col >= 4 else None)
        right = _THIN if col == 1 else (inner if col >= 4 else None)
        ws.cell(r, col).border = Border(left=left, right=right, top=top, bottom=bottom)
```
4. `_header`: remove the `_LINE` border; after filling the two header rows call `_frame(ws, r, summary, top=_MED)` for row `r` and `_frame(ws, r + 1, summary, bottom=_MED)` for row `r + 1`; also set `Alignment(horizontal="centerContinuous")` on cells (r, 2) and (r, 3), (r+1, 2), (r+1, 3).
5. `add_ho_sheet`: sheet name `"BGT HO Report per CC"`; remove the title-row bottom border loop; after the A1..A4 lines add `period = ho.get("period")`: if it parses (`date.fromisoformat(str(period)[:10])` inside try/except ValueError) write `ws["G2"] = <date>` with `number_format = "dd-mmm-yy"`; always write `ws["G3"] = ho.get("cc") or "All"`; give G2 and G3 `_font()` and `_GREEN` fill (G2 only when a date exists).
6. In the row loop call `_frame(ws, r, summary)` for group / account / summary-line rows, and for total rows `_frame(ws, r, summary, top=side, bottom=side)` with `side = _MED if row.get("grand") else _THIN` (replace the old `_LINE` loop); for non-summary total rows also set `Alignment(horizontal="centerContinuous")` on columns 1-3.
7. Keep fonts, number formats, `_CODE = "000-00-000"`, amounts and footnotes unchanged.

- [ ] **Step 3b: Run to verify pass**

Run: `python -m pytest tests/test_mr_exports.py tests/test_mr_ho_report.py -q`
Expected: pass.

- [ ] **Step 4: Report (no commit).**

---

### Task 4: Routes and regression

**Files:**
- Modify: `app/modules/management_report/routes.py`
- Test: `app/tests/test_mr_routes.py`, `app/tests/test_mr_exports.py`

**Interfaces:**
- Consumes: `bgt_report.build_bgt_report`, `config.COMPANIES` (`[{"id", "code", "name"}]`), `service.query_append`, `service.get_active_meta` (`cc_names`, `period`).

- [ ] **Step 1: Write the failing tests**

In `app/tests/test_mr_routes.py` (or `test_mr_exports.py`, wherever the export route tests live) add:

```python
def test_export_first_sheet_follows_the_reference_layout(client):
    from openpyxl import load_workbook
    login(client)
    svc.save_upload(2, "a.xlsb", "u", [
        mkrow(cc="AAA", coa="70105120", mm=1, mm1=1, bgt=10.0, act=4.0,
              category="01 - Rental, Tax", description="Rent"),
        mkrow(cc="AAA", coa="70105120", mm=9, mm1=9, bgt=6.0,
              category="01 - Rental, Tax", description="Rent"),
    ], meta={"cc_names": {"AAA": "Alpha Unit"}, "period": "2026-08-31"})
    wb = load_workbook(io.BytesIO(client.get("/management-report/export?cc=AAA").data))
    assert wb.sheetnames == ["BGT Report per CC", "BGT HO Report per CC", "Append"]
    ws = wb["BGT Report per CC"]
    assert ws["C1"].value == "President Office & ETF – Alpha Unit"
    assert ws["A2"].value == "AAA" and ws["A3"].value == "ETF - Alpha Unit"
    assert ws["C10"].value == "OPEX"
    assert (ws["D10"].value, ws["E10"].value, ws["I10"].value) == (16, 10, 4)
    # mm filter sets the Period, full year stays the whole year
    ws = load_workbook(io.BytesIO(client.get("/management-report/export?cc=AAA&mm=10").data))["BGT Report per CC"]
    assert (ws["D10"].value, ws["E10"].value) == (16, 16)
    assert ws["D4"].value.month == 10
```

(Keep `ETF` for company 2; for company 1 the prefix is `SMT`.)

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_routes.py -q -k reference_layout`
Expected: FAIL.

- [ ] **Step 3: Implement in `routes.py`**

1. Imports: `import config`, `from modules.management_report import bgt_report`.
2. Add a helper below `_ho_for`:

```python
def _company_code(company_id) -> str:
    return next((c["code"] for c in config.COMPANIES if c["id"] == company_id), "")


def _bgt_for(company_id, real_cc, filters, title, meta):
    """Sheet 1 data: lines of the year (no month filter) so full-year and YTD columns can both be filled."""
    rows = service.query_append(company_id, real_cc, filters["yy"], None, filters["coas"])["rows"]
    bgt = bgt_report.build_bgt_report(rows, filters["yy"], filters["mm"], meta.get("period"))
    code = real_cc or "All"
    bgt.update(title=title, cc_code=code, cc_desc=(meta["cc_names"].get(code) or code) if real_cc else "All",
               company_code=_company_code(company_id))
    return bgt
```
3. In `export_one`: after the `report["title"]` assignment compute `meta = service.get_active_meta(company_id)`, `bgt = _bgt_for(company_id, real, f, report["title"], meta)` and call `exports.build_cc_workbook(report, f, ho, append_rows, bgt)`.
4. In `export_all`: inside the loop add `bgt_by_cc[cc] = _bgt_for(company_id, cc, f, report["title"], meta)` (create `bgt_by_cc = {}`), and call `exports.build_zip(reports, f, ho_by_cc, append_by_cc, bgt_by_cc)`.
5. Update remaining sheet-name assertions in `tests/test_mr_exports.py` / `tests/test_mr_routes.py` that go through the routes: `["Report", "BGT HO Report per CC", "Append"]` becomes `["BGT Report per CC", "BGT HO Report per CC", "Append"]`; the assertion `wb["Report"]["A1"].value.endswith("TFKHAR")` becomes `wb["BGT Report per CC"]["C1"].value.endswith("TFKHAR")`; zip tests that go through `/export-all` expect the new first name too. Tests that call `build_cc_workbook`/`build_zip` directly without `bgt` keep `Report`.

- [ ] **Step 4: Run to verify pass, then the whole MR suite**

Run: `python -m pytest tests/test_mr_bgt_report.py tests/test_mr_bgt_exports.py tests/test_mr_exports.py tests/test_mr_routes.py tests/test_mr_ho_report.py tests/test_mr_report.py tests/test_mr_service.py tests/test_dashboard.py -q`
Expected: all pass (about 140+).

- [ ] **Step 5: Manual comparison (controller)**

Build an export for a demo CC on a throwaway instance (not the user's DB) and compare its sheet 1 and 2 styles with the reference file cell by cell for the key cells (fills, fonts, merges, widths, hidden rows). Report differences.

- [ ] **Step 6: Report (no commit).**
