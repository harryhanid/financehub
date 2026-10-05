# Management Report: 3 Tabs, HO Report, Two-Sheet Export - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an HO Report (sheet `BGT HO Report per CC` of the Excel master) to the Management Report module, split the page into tabs (Data Sync / Report / HO Report) and make "Export" produce one workbook per CC with two sheets (`Report`, `HO Report`).

**Architecture:** The HO layout (190 GL accounts, groups, subtotal and summary formulas) is extracted once from Excel into `ho_template.json`; `ho_report.py` fills it with per-COA sums of the active snapshot (x1000, Rp 000). Sync additionally stores workbook metadata (CC descriptions, report period). A new `ho_exports.py` writes the HO sheet. Routes serve HTML fragments so filters refresh the visible tab without a page reload.

**Tech Stack:** Flask, SQLite (`database.get_conn`), `pyxlsb` (read .xlsb), `openpyxl` (write .xlsx), `pywin32` + Excel (template extraction and cross-check only), pytest.

Spec: `docs/superpowers/specs/2026-10-05-management-report-ho-tabs-design.md`

## Global Constraints

- Work in `C:\Financehub\app` (the live Flask app). Run pytest from there: `cd C:\Financehub\app && python -m pytest ...`. All paths below are relative to `C:\Financehub\app` unless they start with `docs/`.
- **No git operations** (`add`, `commit`, `stash`, `checkout`, ...) in `C:\Financehub`: the tree holds the user's uncommitted work. Do not touch files outside this plan.
- Modify existing files with the Edit tool and create files with the Write tool (do not rewrite files through Python/shell scripts).
- Every query is filtered by `company_id`. Amounts in the HO Report are Rp 000: the sum of Append1 values (Rp Mio) x 1000, rounded to 3 decimals.
- HO tab / HO sheet ignore the COA filter (Excel's `MR_2` pivot is not tied to it); CC (incl. "All Cost Center" = `cc=None`), YY and MM apply.
- Excel's HO template is reproduced exactly, including its quirks; Flow only adds warnings (`unmapped`, `summary_missing`).
- Existing behaviour must keep working: all current `tests/test_mr_*.py` pass after each task (except the two assertions this plan explicitly changes in Task 5). Known unrelated failure in the full suite: `tests/test_sponsorship_routes.py::test_input_page_has_cat1_search_and_lembaga_datalist`; run only `tests/test_mr_*.py tests/test_dashboard.py`.
- The Flask templates are cached until the server restarts; the browser check in Task 6 uses a throwaway instance.
- Sample master workbook for real-data tests: `C:\Users\25010160\Downloads\Management Report - MASTER.xlsb` (override with env `MR_SAMPLE_XLSB`); those tests skip when it is missing.

## File Structure

| File | Responsibility |
|---|---|
| `scripts/extract_ho_template.py` | (create) Excel COM tool: sheet `BGT HO Report per CC` -> `ho_template.json` |
| `scripts/crosscheck_ho_with_excel.py` | (create) Excel COM tool: compare Flow's HO figures with Excel's for chosen CCs |
| `modules/management_report/ho_template.json` | (generated) HO layout |
| `modules/management_report/ho_template.py` | (create) `load_template()` |
| `modules/management_report/ho_report.py` | (create) `compute_ho`, `build_ho_report`, `period_label` |
| `modules/management_report/ho_exports.py` | (create) `add_ho_sheet(wb, ho)` |
| `modules/management_report/parser.py` | (modify) `build_meta`, `read_meta` |
| `modules/management_report/service.py` | (modify) `meta` column, `get_active_meta`, `aggregate_by_coa` |
| `modules/management_report/sync.py` | (modify) metadata in hash and summary |
| `modules/management_report/exports.py` | (modify) second sheet, title, zip |
| `modules/management_report/routes.py` | (rewrite) tabs data, `/ho-table`, exports with HO, sync with metadata |
| `templates/management_report/index.html` | (rewrite) tabs |
| `templates/management_report/_report_table.html` | (modify) title |
| `templates/management_report/_ho_table.html` | (create) HO fragment |
| `tests/test_mr_ho_template.py`, `test_mr_meta.py`, `test_mr_ho_report.py` | (create) |
| `tests/test_mr_exports.py`, `test_mr_routes.py` | (modify) |

---

### Task 1: HO template extraction and loader

**Files:**
- Create: `scripts/extract_ho_template.py`
- Create: `modules/management_report/ho_template.py`
- Generate: `modules/management_report/ho_template.json`
- Test: `tests/test_mr_ho_template.py`

**Interfaces:**
- Produces: `load_template() -> dict` (cached) with shape
  ```
  {"org": str, "location": str,
   "sections": [{"key": "capex"|"opex"|"summary", "title": str, "rows": [ROW, ...]}]}
  ROW = {"id": int (= Excel row number), "type": "group", "label": str}
      | {"id": int, "type": "account", "code": str, "label": str, "note": str|None}
      | {"id": int, "type": "total", "label": str, "of": [row ids]}                       # capex/opex group and grand totals
      | {"id": int, "type": "total", "nomor": str, "label": str, "of": [row ids]}         # summary lines (last one = grand)
  ```
  `of` lists the ids of account/total rows that the row sums (ids are unique across sections; summary rows reference opex rows).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_mr_ho_template.py`:

```python
import importlib.util
import os
import re

from modules.management_report.ho_template import load_template

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "extract_ho_template.py")


def _rows(tpl):
    return [r for s in tpl["sections"] for r in s["rows"]]


def test_three_sections_and_190_unique_accounts():
    tpl = load_template()
    assert [s["key"] for s in tpl["sections"]] == ["capex", "opex", "summary"]
    accounts = [r for r in _rows(tpl) if r["type"] == "account"]
    assert len(accounts) == 190
    assert len({a["code"] for a in accounts}) == 190
    assert tpl["org"] == "President Office & ETF"
    assert tpl["location"].startswith("Head Office")


def test_row_ids_are_unique_and_every_reference_resolves():
    rows = _rows(load_template())
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    by_id = {r["id"]: r for r in rows}
    for r in rows:
        if r["type"] == "total":
            assert r["of"], r["id"]
            for i in r["of"]:
                assert by_id[i]["type"] in ("account", "total"), (r["id"], i)


def test_known_rows_match_the_excel_sheet():
    by_id = {r["id"]: r for r in _rows(load_template())}
    assert by_id[124]["code"] == "70105120"
    assert by_id[124]["label"] == "Equipment Rent Expense - 3rd Party"
    assert by_id[43]["label"] == "Total Capex" and len(by_id[43]["of"]) == 6
    assert by_id[263]["label"] == "Grand Total included Depreciation" and len(by_id[263]["of"]) == 20
    assert by_id[281]["label"] == "Rent, Tax, and License Expense" and by_id[281]["of"] == [137]
    assert by_id[298]["label"] == "Total" and len(by_id[298]["of"]) == 22


def test_sections_end_with_their_grand_total_and_summary_title_has_no_year():
    tpl = load_template()
    last_total = {s["key"]: [r for r in s["rows"] if r["type"] == "total"][-1]["id"]
                  for s in tpl["sections"]}
    assert last_total == {"capex": 43, "opex": 263, "summary": 298}
    assert not re.search(r"\d{4}", tpl["sections"][2]["title"])


def test_account_notes_are_kept():
    notes = {r["code"] for r in _rows(load_template()) if r["type"] == "account" and r.get("note")}
    assert notes == {"70004113", "701193100", "701078002", "701078003"}


def test_formula_reference_parser():
    spec = importlib.util.spec_from_file_location("extract_ho_template", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    kinds = {r: "account" for r in list(range(72, 84)) + list(range(100, 105))}
    assert mod._refs("=SUM(D72:D83,D100:D104)", kinds) == list(range(72, 84)) + list(range(100, 105))
    assert mod._refs("=D70+D107", {70: "total", 107: "total"}) == [70, 107]
    assert mod._refs("=SUM(D1:D3)", {2: "group"}) == []
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_ho_template.py -v`
Expected: collection ERROR `ModuleNotFoundError: No module named 'modules.management_report.ho_template'`

- [ ] **Step 3: Create the loader and the extraction script**

Create `modules/management_report/ho_template.py`:

```python
"""Layout of the HO Report, extracted from the Excel master into ho_template.json."""
import functools
import json
import os

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ho_template.json")


@functools.lru_cache(maxsize=1)
def load_template() -> dict:
    with open(_PATH, encoding="utf-8") as f:
        return json.load(f)
```

Create `scripts/extract_ho_template.py`:

```python
"""Extract the layout of sheet 'BGT HO Report per CC' into ho_template.json.

Run on the master workbook whenever the HO template in Excel changes
(for example a new GL account):

    python scripts/extract_ho_template.py "C:\\path\\Management Report - MASTER.xlsb"

Excel (desktop) must be installed: formulas cannot be read from .xlsb otherwise.
The workbook is copied first and opened read-only with macros disabled; nothing is saved.
"""
import json
import os
import re
import shutil
import sys
import tempfile

import win32com.client

SHEET = "BGT HO Report per CC"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "modules", "management_report", "ho_template.json")

# Row bounds of the three blocks in the Excel sheet (1-based, inclusive).
SECTIONS = [
    {"key": "capex", "title_row": 5, "first": 8, "last": 43},
    {"key": "opex", "title_row": 51, "first": 54, "last": 263},
    {"key": "summary", "title_row": 271, "first": 275, "last": 298},
]
_REF = re.compile(r"\$?D\$?(\d+)(?::\$?D\$?(\d+))?")


def _text(v):
    return "" if v is None else str(v).strip()


def _code(v):
    if isinstance(v, (int, float)) and float(v).is_integer():
        return str(int(v))
    return None


def _refs(formula: str, row_kinds: dict) -> list:
    """Row numbers a '=SUM(D72:D83,D100:D104)' / '=D70+D107' formula adds up.

    Ranges are expanded to the rows that carry a value (account/total rows)."""
    out = []
    for m in _REF.finditer(formula):
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        out.extend(r for r in range(lo, hi + 1) if row_kinds.get(r) in ("account", "total"))
    return out


def extract(path: str) -> dict:
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3                      # msoAutomationSecurityForceDisable
    wb = xl.Workbooks.Open(os.path.abspath(path), 0, True)
    try:
        ws = wb.Worksheets.Item(SHEET)
        cell = lambda r, c: ws.Cells(r, c)
        out = {"org": _text(cell(1, 1).Value2), "location": _text(cell(2, 1).Value2),
               "sections": []}
        for sec in SECTIONS:
            rows, kinds = [], {}
            for r in range(sec["first"], sec["last"] + 1):
                a, b = cell(r, 1).Value2, cell(r, 2).Value2
                formula = _text(cell(r, 4).Formula)
                note = _text(cell(r, 7).Value2) or None
                if sec["key"] == "summary":
                    if formula.startswith("="):
                        kinds[r] = "total"
                        rows.append({"id": r, "type": "total", "nomor": _text(a),
                                     "label": _text(b), "formula": formula})
                    continue
                if _code(a) and formula.upper().startswith("=XLOOKUP("):
                    kinds[r] = "account"
                    rows.append({"id": r, "type": "account", "code": _code(a),
                                 "label": _text(b), "note": note})
                elif _text(a) and formula.startswith("="):
                    kinds[r] = "total"
                    rows.append({"id": r, "type": "total", "label": _text(a), "formula": formula})
                elif _text(a):
                    rows.append({"id": r, "type": "group", "label": _text(a)})
            out["sections"].append({"key": sec["key"],
                                    "title": _text(cell(sec["title_row"], 1).Value2),
                                    "rows": rows, "_kinds": kinds})
        # Summary rows refer to rows of the opex block: resolve once all blocks are known.
        all_kinds = {}
        for s in out["sections"]:
            all_kinds.update(s["_kinds"])
        for s in out["sections"]:
            for row in s["rows"]:
                if row["type"] == "total":
                    row["of"] = _refs(row.pop("formula"), all_kinds)
            del s["_kinds"]
        # Excel hard-codes a year in the summary title; Flow renders the data year instead.
        for s in out["sections"]:
            if s["key"] == "summary":
                s["title"] = re.sub(r"^Budget\s+\d{4}\s*-\s*", "", s["title"])
        return out
    finally:
        wb.Close(False)
        xl.Quit()


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    tmp = os.path.join(tempfile.mkdtemp(), "master_copy.xlsb")
    shutil.copyfile(argv[1], tmp)                  # never touch the original while Excel has it
    data = extract(tmp)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    n_acc = sum(1 for s in data["sections"] for r in s["rows"] if r["type"] == "account")
    print(f"wrote {os.path.normpath(OUT)}: {n_acc} accounts")


if __name__ == "__main__":
    main(sys.argv)
```

- [ ] **Step 4: Generate the template from the real master workbook**

Run: `python scripts/extract_ho_template.py "C:\Users\25010160\Downloads\Management Report - MASTER.xlsb"`
Expected output: `wrote ...\modules\management_report\ho_template.json: 190 accounts`
(Excel must be installed; it opens and closes invisibly. If the command fails because Excel cannot start, report BLOCKED with the error.)

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_mr_ho_template.py -v`
Expected: 6 passed. If `test_known_rows_match_the_excel_sheet` fails, the master workbook's HO layout differs from the one this plan was written against: report the differing ids instead of editing the expected values.

---

### Task 2: Sync metadata (CC descriptions, report period)

**Files:**
- Modify: `modules/management_report/parser.py` (append)
- Modify: `modules/management_report/service.py`
- Modify: `modules/management_report/sync.py`
- Modify: `modules/management_report/routes.py` (the `sync_excel` function only)
- Test: `tests/test_mr_meta.py`, `tests/test_mr_routes.py` (append one test)

**Interfaces:**
- Produces (parser): `build_meta(report_pairs, period_value) -> {"cc_names": {cc: description}, "period": "YYYY-MM-DD"|None}`; `read_meta(fileobj) -> same shape`, never raises.
- Produces (service): `get_active_meta(company_id) -> {"cc_names": {...}, "period": str|None}` (empty shape when none); `save_upload(..., meta: dict = None)` stores it in new column `mr_upload.meta` (auto-migrated).
- Produces (sync): `compute_hash(rows, meta=None)`; `sync_rows(company_id, filename, uploaded_by, rows, meta=None)`; the stored change summary gains `"meta_changed": bool`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_mr_meta.py`:

```python
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
```

Append to `tests/test_mr_routes.py`:

```python
def test_sync_stores_workbook_metadata(client, monkeypatch):
    login(client)
    monkeypatch.setattr(mr_routes, "read_meta",
                        lambda f: {"cc_names": {"B": "Beta"}, "period": "2026-08-31"})
    _sync(client, monkeypatch, [mkrow(cc="B")])
    assert svc.get_active_meta(2) == {"cc_names": {"B": "Beta"}, "period": "2026-08-31"}
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_meta.py tests/test_mr_routes.py -q`
Expected: collection ERROR (`cannot import name 'build_meta'`) for test_mr_meta.py.

- [ ] **Step 3: Implement the parser part**

In `modules/management_report/parser.py` add `import datetime as _dt` below the existing `from collections import namedtuple` line, and append to the end of the file:

```python
def _excel_date(v):
    try:
        return (_dt.date(1899, 12, 30) + _dt.timedelta(days=int(float(v)))).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def build_meta(report_pairs, period_value) -> dict:
    """CC descriptions from the (code, description) cells of Report!U10:V100 and the report period."""
    names = {}
    for code, name in report_pairs:
        code, name = _text(code), _text(name)
        if code and name and not code.startswith("0x") and not name.startswith("0x"):
            names[code] = name                       # '0x..' is how pyxlsb shows an Excel error cell
    return {"cc_names": names, "period": _excel_date(period_value)}


def read_meta(fileobj) -> dict:
    """Best effort: a missing sheet or cell leaves the field empty, the sync never fails because of it."""
    pairs, period = [], None
    try:
        with open_workbook(fileobj) as wb:
            if "Report" in wb.sheets:
                with wb.get_sheet("Report") as sh:
                    for row in sh.rows():
                        r = row[0].r
                        if r < 9:
                            continue
                        if r > 99:
                            break
                        pairs.append((row[20].v if len(row) > 20 else None,
                                      row[21].v if len(row) > 21 else None))
            if "Parameter" in wb.sheets:
                with wb.get_sheet("Parameter") as sh:
                    for row in sh.rows():
                        if row[0].r == 1:
                            period = row[1].v if len(row) > 1 else None
                            break
                        if row[0].r > 1:
                            break
    except Exception:
        pass
    return build_meta(pairs, period)
```

- [ ] **Step 4: Implement the service part**

In `modules/management_report/service.py`:

(a) In `_DDL`, replace
```
    change_summary TEXT
);
```
with
```
    change_summary TEXT,
    meta           TEXT
);
```
(b) In `ensure_schema`, replace `for col in ("content_hash", "change_summary"):` with `for col in ("content_hash", "change_summary", "meta"):`.
(c) Replace the whole `save_upload` signature-and-first-insert part:
```python
def save_upload(company_id: int, filename: str, uploaded_by: str, rows: list,
                keep: int = KEEP_SNAPSHOTS, content_hash: str = None,
                change_summary: dict = None) -> int:
```
with
```python
def save_upload(company_id: int, filename: str, uploaded_by: str, rows: list,
                keep: int = KEEP_SNAPSHOTS, content_hash: str = None,
                change_summary: dict = None, meta: dict = None) -> int:
```
and replace
```python
            "INSERT INTO mr_upload (company_id, filename, uploaded_by, uploaded_at, row_count, "
            "is_active, content_hash, change_summary) VALUES (?,?,?,?,?,0,?,?)",
            (company_id, filename, uploaded_by, _ts(), len(rows), content_hash,
             json.dumps(change_summary) if change_summary is not None else None))
```
with
```python
            "INSERT INTO mr_upload (company_id, filename, uploaded_by, uploaded_at, row_count, "
            "is_active, content_hash, change_summary, meta) VALUES (?,?,?,?,?,0,?,?,?)",
            (company_id, filename, uploaded_by, _ts(), len(rows), content_hash,
             json.dumps(change_summary) if change_summary is not None else None,
             json.dumps(meta) if meta else None))
```
(d) Add this function directly above `def list_uploads`:
```python
def get_active_meta(company_id: int) -> dict:
    """Metadata read from the master workbook at the last sync (CC descriptions, report period)."""
    empty = {"cc_names": {}, "period": None}
    conn = get_conn()
    try:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT meta FROM mr_upload WHERE company_id=? AND is_active=1", (company_id,)).fetchone()
        if not row or not row["meta"]:
            return empty
        data = json.loads(row["meta"])
        return {"cc_names": data.get("cc_names") or {}, "period": data.get("period")}
    finally:
        conn.close()
```

- [ ] **Step 5: Implement the sync part**

In `modules/management_report/sync.py`:

(a) Replace the whole `compute_hash` function with:
```python
def _norm_meta(meta):
    """Canonical form of the sync metadata; None when it carries no information."""
    if not meta or not (meta.get("cc_names") or meta.get("period")):
        return None
    return {"cc_names": dict(sorted((meta.get("cc_names") or {}).items())),
            "period": meta.get("period")}


def compute_hash(rows: list, meta: dict = None) -> str:
    """Order-independent content hash of parsed rows (floats rounded to 6 decimals) and metadata."""
    lines = sorted(json.dumps([_norm(r[f]) for f in _HASH_FIELDS], ensure_ascii=False)
                   for r in rows)
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    m = _norm_meta(meta)
    if m is not None:
        h.update(b"META\n")
        h.update(json.dumps(m, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()
```
(b) Replace the whole `sync_rows` function with:
```python
def sync_rows(company_id: int, filename: str, uploaded_by: str, rows: list, meta: dict = None) -> dict:
    """Store `rows` (+ metadata) as the new active snapshot unless they equal the active one.

    Returns {"changed": False, "rows": n} when nothing changed, otherwise
    {"changed": True, "upload_id": id, "rows": n, "summary": {...}}.
    """
    new_meta = _norm_meta(meta)
    new_hash = compute_hash(rows, new_meta)
    old_rows = service.load_active_rows(company_id)
    old_meta = _norm_meta(service.get_active_meta(company_id))
    if old_rows:
        old_hash = service.get_active_hash(company_id) or compute_hash(old_rows, old_meta)
        if old_hash == new_hash:
            return {"changed": False, "rows": len(rows)}
    summary = summarize_changes(old_rows, rows)
    summary["meta_changed"] = bool(old_rows) and old_meta != new_meta
    upload_id = service.save_upload(company_id, filename, uploaded_by, rows,
                                    content_hash=new_hash, change_summary=summary, meta=new_meta)
    return {"changed": True, "upload_id": upload_id, "rows": len(rows), "summary": summary}
```

- [ ] **Step 6: Pass the metadata through the sync route**

In `modules/management_report/routes.py`:

(a) Replace `from modules.management_report.parser import ParseError, read_append1` with `from modules.management_report.parser import ParseError, read_append1, read_meta`.
(b) In `sync_excel`, replace
```python
    try:
        result = read_append1(io.BytesIO(f.read()))
        if not result.rows:
            raise ParseError("Tidak ada baris data yang valid di sheet Append1.")
    except ParseError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    out = mr_sync.sync_rows(company_id, f.filename, get_jwt().get("username", ""), result.rows)
```
with
```python
    data = f.read()
    try:
        result = read_append1(io.BytesIO(data))
        if not result.rows:
            raise ParseError("Tidak ada baris data yang valid di sheet Append1.")
    except ParseError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    meta = read_meta(io.BytesIO(data))
    out = mr_sync.sync_rows(company_id, f.filename, get_jwt().get("username", ""), result.rows,
                            meta=meta)
```
and replace
```python
        pesan = (f"Sync selesai: {s['rows_before']} → {s['rows_after']} baris "
                 f"({result.dropped} baris dilewati).")
```
with
```python
        pesan = (f"Sync selesai: {s['rows_before']} → {s['rows_after']} baris "
                 f"({result.dropped} baris dilewati).")
        if s.get("meta_changed"):
            pesan += " Deskripsi CC / periode laporan diperbarui."
```

- [ ] **Step 7: Run the tests**

Run: `python -m pytest tests/test_mr_meta.py tests/test_mr_sync.py tests/test_mr_routes.py tests/test_mr_service.py tests/test_mr_parser.py -q`
Expected: all pass (no failures from existing sync/route tests).

---

### Task 3: HO calculation

**Files:**
- Modify: `modules/management_report/service.py` (add `aggregate_by_coa`)
- Create: `modules/management_report/ho_report.py`
- Test: `tests/test_mr_ho_report.py`

**Interfaces:**
- Consumes: `load_template()` (Task 1), `service.get_active_meta`, `service.get_filter_options` (Task 2 / existing).
- Produces:
  - `service.aggregate_by_coa(company_id, cc=None, yy=None, mm=None) -> {coa: (bgt, pta, act)}`
  - `ho_report.period_label(period_iso) -> "s/d Aug"` (`""` if unknown)
  - `ho_report.compute_ho(tpl, agg) -> {"sections": [...], "unmapped": [...], "summary_missing": [...]}` where each section is `{"key","title","rows","grand_id"}`; account/total rows gain `bgt, pta, act` (Rp 000); total rows gain `grand: bool`; rows lose `of`.
  - `ho_report.build_ho_report(company_id, cc=None, yy=None, mm=None) -> dict` = `compute_ho(...)` plus `has_data, org, location, cc, division, period_label, year`; the summary section title becomes `"Budget <year> - Operating Expense Summary (in Rp. 000)"` when a year is known.
  - `unmapped` items: `{"coa","label","bgt","pta","act"}` (label `None` if the COA is not in the template); `summary_missing` items: same keys.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_mr_ho_report.py`:

```python
import collections
import io
import os

import pytest

from modules.management_report import service as svc
from modules.management_report.ho_report import build_ho_report, period_label
from modules.management_report.parser import read_append1
from tests.test_mr_service import mkrow

SAMPLE = os.environ.get('MR_SAMPLE_XLSB',
                        r'C:\Users\25010160\Downloads\Management Report - MASTER.xlsb')


def _row(ho, section, row_id):
    sec = next(s for s in ho["sections"] if s["key"] == section)
    return next(r for r in sec["rows"] if r["id"] == row_id)


def seed(rows, meta=None):
    svc.save_upload(1, "m.xlsb", "u", rows, meta=meta)


def test_amounts_are_in_rp_000_and_roll_up_to_totals():
    seed([mkrow(cc="AAA", coa="70105120", bgt=3.2, pta=0.5, act=0.1),
          mkrow(cc="AAA", coa="70106200", bgt=53.3),
          mkrow(cc="AAA", coa="70106400", bgt=36.0)])
    ho = build_ho_report(1, "AAA")
    assert ho["has_data"] is True
    acc = _row(ho, "opex", 124)
    assert (acc["bgt"], acc["pta"], acc["act"]) == (3200.0, 500.0, 100.0)
    assert _row(ho, "opex", 137)["bgt"] == 3200.0           # Total - 701-05-xxx
    assert _row(ho, "opex", 143)["bgt"] == 89300.0          # Total - 701-06-xxx
    assert _row(ho, "opex", 263)["bgt"] == 92500.0 and _row(ho, "opex", 263)["grand"] is True
    assert _row(ho, "summary", 281)["bgt"] == 3200.0        # Rent, Tax, and License Expense
    assert _row(ho, "summary", 282)["bgt"] == 89300.0       # Transport & Travelling Expense
    assert _row(ho, "summary", 298)["bgt"] == 92500.0
    assert ho["unmapped"] == [] and ho["summary_missing"] == []


def test_cost_center_year_and_month_filters_apply_but_not_a_coa_filter():
    seed([mkrow(cc="AAA", coa="70105120", bgt=1.0, mm=1, yy=26),
          mkrow(cc="BBB", coa="70105120", bgt=2.0, mm=2, yy=26),
          mkrow(cc="BBB", coa="70105120", bgt=4.0, mm=2, yy=25)])
    assert _row(build_ho_report(1, "AAA"), "opex", 124)["bgt"] == 1000.0
    assert _row(build_ho_report(1, None), "opex", 124)["bgt"] == 7000.0      # All Cost Center
    assert _row(build_ho_report(1, None, mm=2), "opex", 124)["bgt"] == 6000.0
    assert _row(build_ho_report(1, None, yy=25), "opex", 124)["bgt"] == 4000.0
    assert build_ho_report(1, "AAA", mm=12)["has_data"] is False
    assert build_ho_report(2, "AAA")["has_data"] is False                    # other company


def test_coa_outside_the_template_is_unmapped_and_not_counted():
    seed([mkrow(cc="AAA", coa="71000110", act=-97.5), mkrow(cc="AAA", coa="70105120", bgt=1.0)])
    ho = build_ho_report(1, "AAA")
    assert ho["unmapped"] == [{"coa": "71000110", "label": None,
                               "bgt": 0.0, "pta": 0.0, "act": -97500.0}]
    assert _row(ho, "opex", 263)["act"] == 0.0


def test_listed_account_outside_every_group_total_is_unmapped():
    seed([mkrow(cc="AAA", coa="70101300", bgt=2.0)])          # 'Workshop Exp' sits below its group total
    ho = build_ho_report(1, "AAA")
    assert [u["coa"] for u in ho["unmapped"]] == ["70101300"]
    assert ho["unmapped"][0]["label"] == "Workshop Exp"
    assert _row(ho, "opex", 263)["bgt"] == 0.0


def test_account_missing_from_the_summary_is_reported():
    seed([mkrow(cc="AAA", coa="70102114", bgt=12.0, act=5.6),
          mkrow(cc="AAA", coa="70105120", bgt=1.0)])
    ho = build_ho_report(1, "AAA")
    assert _row(ho, "opex", 263)["bgt"] == 13000.0
    assert _row(ho, "summary", 298)["bgt"] == 1000.0
    assert ho["summary_missing"] == [{"coa": "70102114", "label": "NS BPJT TK (JKK & JKM) Allowance",
                                      "bgt": 12000.0, "pta": 0.0, "act": 5600.0}]


def test_titles_period_and_division_come_from_the_sync_metadata():
    seed([mkrow(cc="AAA", coa="70105120", bgt=1.0)],
         meta={"cc_names": {"AAA": "Alpha Unit"}, "period": "2026-08-31"})
    ho = build_ho_report(1, "AAA")
    assert ho["org"] == "President Office & ETF" and ho["location"].startswith("Head Office")
    assert ho["division"] == "Alpha Unit" and ho["period_label"] == "s/d Aug"
    summary = next(s for s in ho["sections"] if s["key"] == "summary")
    assert summary["title"] == "Budget 2026 - Operating Expense Summary (in Rp. 000)"
    assert build_ho_report(1, None)["division"] == "All"
    assert build_ho_report(1, "ZZZ")["division"] == "ZZZ"


def test_year_filter_drives_the_summary_title_and_missing_metadata_is_tolerated():
    seed([mkrow(cc="AAA", coa="70105120", bgt=1.0, yy=25)])
    ho = build_ho_report(1, "AAA", yy=25)
    assert ho["year"] == 2025 and ho["period_label"] == "" and ho["division"] == "AAA"
    summary = next(s for s in ho["sections"] if s["key"] == "summary")
    assert summary["title"].startswith("Budget 2025 - ")


def test_period_label():
    assert period_label("2026-08-31") == "s/d Aug"
    assert period_label("2026-12-01") == "s/d Dec"
    assert period_label(None) == "" and period_label("garbage") == ""


# ---------- real master workbook ----------

@pytest.fixture
def master():
    try:
        with open(SAMPLE, "rb") as f:
            return f.read()
    except OSError:
        pytest.skip("sample master workbook not available")


def _sheet(data, name):
    from pyxlsb import open_workbook
    with open_workbook(io.BytesIO(data)) as wb:
        with wb.get_sheet(name) as sh:
            return [[c.v for c in r] for r in sh.rows()]


def test_every_computed_cell_matches_the_excel_ho_sheet(master):
    report = _sheet(master, "Report")
    cc, yy, mm = report[3][1], report[4][1], report[5][1]       # page filters B4:B6
    rows = read_append1(io.BytesIO(master)).rows
    if yy != "All" or mm != "All" or (cc != "All" and cc not in {r["cc"] for r in rows}):
        pytest.skip("master workbook is filtered by YY/MM or several CCs; reconciliation needs one CC")
    svc.save_upload(1, "m.xlsb", "u", rows)
    ho = build_ho_report(1, None if cc == "All" else cc)
    sheet = _sheet(master, "BGT HO Report per CC")
    checked = 0
    for s in ho["sections"]:
        for r in s["rows"]:
            if "bgt" not in r:
                continue
            expected = [float(v) if isinstance(v, (int, float)) else 0.0
                        for v in sheet[r["id"] - 1][3:6]]        # columns D:F of the Excel row
            assert [r["bgt"], r["pta"], r["act"]] == pytest.approx(expected, abs=1e-3), \
                (s["key"], r["id"], r.get("label"))
            checked += 1
    assert checked >= 240


def test_invariants_hold_for_every_cost_center(master):
    rows = read_append1(io.BytesIO(master)).rows
    svc.save_upload(1, "m.xlsb", "u", rows)
    for cc in sorted({r["cc"] for r in rows}) + [None]:
        raw = collections.defaultdict(float)
        for r in rows:
            if cc is None or r["cc"] == cc:
                for key in ("bgt", "pta", "act"):
                    raw[key] += r[key] * 1000
        ho = build_ho_report(1, cc)
        grand = {s["key"]: next(r for r in s["rows"] if r.get("grand")) for s in ho["sections"]}
        for key in ("bgt", "pta", "act"):
            unmapped = sum(u[key] for u in ho["unmapped"])
            missing = sum(m[key] for m in ho["summary_missing"])
            assert raw[key] == pytest.approx(
                grand["capex"][key] + grand["opex"][key] + unmapped, abs=1e-3), (cc, key)
            assert grand["opex"][key] == pytest.approx(
                grand["summary"][key] + missing, abs=1e-3), (cc, key)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_ho_report.py -q`
Expected: collection ERROR `ModuleNotFoundError: ... ho_report`.

- [ ] **Step 3: Add `aggregate_by_coa` to the service**

In `modules/management_report/service.py`, append at the end of the file:

```python
def aggregate_by_coa(company_id: int, cc=None, yy=None, mm=None) -> dict:
    """{coa: (bgt, pta, act)} of the active snapshot; cc=None means all cost centers."""
    uid = get_active_upload_id(company_id)
    if uid is None:
        return {}
    where, params = _where(uid, cc, yy, mm, None)
    conn = get_conn()
    try:
        cur = conn.execute(
            f"SELECT coa, SUM(bgt), SUM(pta), SUM(act) FROM mr_append WHERE {where} GROUP BY coa",
            params)
        return {r[0]: (r[1] or 0.0, r[2] or 0.0, r[3] or 0.0) for r in cur.fetchall() if r[0]}
    finally:
        conn.close()
```

- [ ] **Step 4: Create `modules/management_report/ho_report.py`**

```python
"""Management Report: HO Report (sheet 'BGT HO Report per CC') computed from the active snapshot."""
from modules.management_report import service
from modules.management_report.ho_template import load_template

_ZERO = (0.0, 0.0, 0.0)
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def period_label(period_iso) -> str:
    try:
        month = int(str(period_iso)[5:7])
    except (TypeError, ValueError):
        return ""
    return f"s/d {_MONTHS[month - 1]}" if 1 <= month <= 12 else ""


def _accounts_under(row_id, by_id) -> set:
    row = by_id[row_id]
    if row["type"] == "account":
        return {row_id}
    out = set()
    for i in row["of"]:
        out |= _accounts_under(i, by_id)
    return out


def _nonzero(values) -> bool:
    return any(abs(v) > 1e-9 for v in values)


def compute_ho(tpl: dict, agg: dict) -> dict:
    """Fill the template with amounts (x1000, Rp 000) from agg = {coa: (bgt, pta, act)}."""
    by_id = {r["id"]: r for s in tpl["sections"] for r in s["rows"]}
    sections, vals = [], {}
    for s in tpl["sections"]:
        totals = [r["id"] for r in s["rows"] if r["type"] == "total"]
        grand_id = totals[-1] if totals else None
        rows = []
        for r in s["rows"]:
            row = dict(r)
            row.pop("of", None)
            if r["type"] == "account":
                a = agg.get(r["code"], _ZERO)
                vals[r["id"]] = [a[0] * 1000, a[1] * 1000, a[2] * 1000]
            elif r["type"] == "total":
                vals[r["id"]] = [sum(vals[i][k] for i in r["of"]) for k in range(3)]
                row["grand"] = r["id"] == grand_id
            if r["id"] in vals:
                row["bgt"], row["pta"], row["act"] = (round(v, 3) for v in vals[r["id"]])
            rows.append(row)
        sections.append({"key": s["key"], "title": s["title"], "rows": rows, "grand_id": grand_id})

    grand = {s["key"]: s["grand_id"] for s in sections}
    counted = _accounts_under(grand["capex"], by_id) | _accounts_under(grand["opex"], by_id)
    in_summary = _accounts_under(grand["summary"], by_id)
    counted_codes = {by_id[i]["code"] for i in counted}

    unmapped = []                                   # data that no grand total contains
    for coa in sorted(agg):
        a = agg[coa]
        if coa not in counted_codes and _nonzero(a):
            label = next((r["label"] for r in by_id.values()
                          if r["type"] == "account" and r["code"] == coa), None)
            unmapped.append({"coa": coa, "label": label, "bgt": round(a[0] * 1000, 3),
                             "pta": round(a[1] * 1000, 3), "act": round(a[2] * 1000, 3)})

    summary_missing = []                            # in the Opex grand total, in no summary line
    for i in sorted(_accounts_under(grand["opex"], by_id) - in_summary,
                    key=lambda i: by_id[i]["code"]):
        v = vals[i]
        if _nonzero(v):
            summary_missing.append({"coa": by_id[i]["code"], "label": by_id[i]["label"],
                                    "bgt": round(v[0], 3), "pta": round(v[1], 3),
                                    "act": round(v[2], 3)})
    return {"sections": sections, "unmapped": unmapped, "summary_missing": summary_missing}


def _full_year(yy):
    if yy is None:
        return None
    return yy + 2000 if yy < 100 else yy


def build_ho_report(company_id: int, cc=None, yy=None, mm=None) -> dict:
    """HO Report for the active snapshot; cc=None means All Cost Center. The COA filter does not apply."""
    tpl = load_template()
    agg = service.aggregate_by_coa(company_id, cc, yy, mm)
    meta = service.get_active_meta(company_id)
    out = compute_ho(tpl, agg)
    year = _full_year(yy)
    if year is None:
        yys = service.get_filter_options(company_id)["yys"]
        year = _full_year(max(yys)) if yys else None
    if year:
        for s in out["sections"]:
            if s["key"] == "summary":
                s["title"] = f"Budget {year} - {s['title']}"
    out.update({
        "has_data": bool(agg),
        "org": tpl["org"],
        "location": tpl["location"],
        "cc": cc,
        "division": "All" if cc is None else meta["cc_names"].get(cc, cc),
        "period_label": period_label(meta.get("period")),
        "year": year,
    })
    return out
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_mr_ho_report.py -v`
Expected: all pass, including `test_every_computed_cell_matches_the_excel_ho_sheet` (it must report `checked >= 240`, not skip, when the sample workbook exists) and `test_invariants_hold_for_every_cost_center`. If a cell mismatches, report row id and values; do not change expected values.

---

### Task 4: Export module: HO sheet and two-sheet workbook

**Files:**
- Create: `modules/management_report/ho_exports.py`
- Modify: `modules/management_report/exports.py`
- Test: `tests/test_mr_exports.py` (append)

**Interfaces:**
- Consumes: the `ho` dict of `build_ho_report` (Task 3).
- Produces: `ho_exports.add_ho_sheet(wb, ho) -> None` (adds sheet `HO Report`); `exports.build_cc_workbook(report, filters=None, ho=None) -> bytes` (sheet `Report`, plus `HO Report` when `ho` is given; title cell uses `report["title"]` when present); `exports.build_zip(reports, filters=None, ho_by_cc=None) -> bytes` (`ho_by_cc` maps the report's `cc` to its `ho` dict).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mr_exports.py` (the file already imports `io`, `zipfile`, `pytest`, `load_workbook`, `svc`, `build_cc_workbook`, `build_zip`, `mkrow`; add `from modules.management_report import ho_report as hr` next to the other imports):

```python
@pytest.fixture
def ho_seeded():
    svc.save_upload(2, "a.xlsb", "u", [
        mkrow(cc="AAA", category="01 - Rental", coa="70105120", bgt=3.2, act=0.5, description="Rent"),
        mkrow(cc="AAA", category="01 - Rental", coa="71000110", act=-97.5, description="Interest"),
        mkrow(cc="AAA", category="01 - Rental", coa="70102114", bgt=12.0, act=5.6, description="BPJS"),
    ], meta={"cc_names": {"AAA": "Alpha Unit"}, "period": "2026-08-31"})


def _row_with(ws, value, col):
    return next(r for r in range(1, ws.max_row + 1) if ws.cell(r, col).value == value)


def _ho_workbook():
    rep = svc.build_report(2, "AAA")
    rep["title"] = "President Office & ETF – Alpha Unit"
    return load_workbook(io.BytesIO(build_cc_workbook(rep, {}, hr.build_ho_report(2, "AAA"))))


def test_workbook_gets_a_second_sheet_with_the_ho_report(ho_seeded):
    wb = _ho_workbook()
    assert wb.sheetnames == ["Report", "HO Report"]
    assert wb["Report"]["A1"].value == "President Office & ETF – Alpha Unit"
    ws = wb["HO Report"]
    assert ws["A1"].value == "President Office & ETF" and ws["A2"].value.startswith("Head Office")
    assert ws["A4"].value == "Division/Dept.: Alpha Unit"
    r = _row_with(ws, 70105120, 1)
    assert ws.cell(r, 1).number_format == "000-00-000"
    assert ws.cell(r, 2).value == "Equipment Rent Expense - 3rd Party"
    assert (ws.cell(r, 4).value, ws.cell(r, 5).value, ws.cell(r, 6).value) == (3200.0, 0.0, 500.0)
    assert ws.cell(r, 4).number_format.startswith("_(* #,##0_)")
    t = _row_with(ws, "Total - 701-05-xxx", 1)
    assert ws.cell(t, 4).value == 3200.0 and ws.cell(t, 1).font.bold is True
    g = _row_with(ws, "Grand Total included Depreciation", 1)
    assert ws.cell(g, 4).value == 15200.0                    # 3,200 + 12,000 (70102114 counts in Opex)
    texts = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
    assert texts.count("s/d Aug") >= 9                        # 3 sections x 3 columns
    summary_total = _row_with(ws, "Total", 2)
    assert ws.cell(summary_total, 4).value == 3200.0         # 70102114 is in no summary line


def test_ho_sheet_footnotes_for_unmapped_coa_and_summary_gap(ho_seeded):
    ws = _ho_workbook()["HO Report"]
    g = _row_with(ws, "Grand Total included Depreciation", 1)
    assert str(ws.cell(g + 1, 1).value).startswith("Tidak termasuk COA 71000110")
    assert "ACT -97,500" in ws.cell(g + 1, 1).value
    s = _row_with(ws, "Total", 2)
    note = str(ws.cell(s + 1, 1).value)
    assert note.startswith("Tidak ada di ringkasan") and "70102114" in note


def test_zip_has_both_sheets_per_cc(ho_seeded):
    reps = [svc.build_report(2, "AAA")]
    zf = zipfile.ZipFile(io.BytesIO(build_zip(reps, {}, {"AAA": hr.build_ho_report(2, "AAA")})))
    assert zf.namelist() == ["AAA.xlsx"]
    assert load_workbook(io.BytesIO(zf.read("AAA.xlsx"))).sheetnames == ["Report", "HO Report"]


def test_workbook_without_ho_data_keeps_a_single_sheet(ho_seeded):
    wb = load_workbook(io.BytesIO(build_cc_workbook(svc.build_report(2, "AAA"))))
    assert wb.sheetnames == ["Report"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_exports.py -q`
Expected: the 4 new tests FAIL (`build_cc_workbook() takes from 1 to 2 positional arguments` / missing HO sheet); existing tests still pass.

- [ ] **Step 3: Create `modules/management_report/ho_exports.py`**

```python
"""HO Report sheet of the per-CC export; mirrors 'BGT HO Report per CC' of the Excel master."""
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

_BLUE = "0000FF"
_NUM = '_(* #,##0_);_(* (#,##0);_(* "-"_);_(@_)'
_CODE = "000-00-000"
_HEAD = PatternFill("solid", fgColor="FFFF99")
_AMOUNT = PatternFill("solid", fgColor="CCFFFF")
_LINE = Border(bottom=Side(style="thin"))
_WIDTHS = {"A": 16.5, "B": 51.3, "C": 8.5, "D": 16, "E": 14, "F": 16, "G": 30}
_KEYS = (("bgt", "BGT"), ("pta", "PTA"), ("act", "ACT"))


def _font(size=11, bold=False, color=None, italic=False):
    return Font(name="Arial", size=size, bold=bold, color=color, italic=italic)


def _header(ws, r, summary, period):
    top = {1: "Nomor" if summary else "GL Account", 2: "Keterangan" if summary else "Description",
           4: "Budget", 5: "PTA", 6: "Actual"}
    sub = {1: "Prakiraan" if summary else None, 4: period, 5: period, 6: period}
    for col in range(1, 7):
        for row, vals in ((r, top), (r + 1, sub)):
            c = ws.cell(row, col, vals.get(col))
            c.font = _font(bold=True)
            c.fill = _HEAD
            c.alignment = Alignment(horizontal="center")
        ws.cell(r + 1, col).border = _LINE
    return r + 2


def _amounts(ws, r, row, fill=None, bold=False, color=None):
    for col, key in zip((4, 5, 6), ("bgt", "pta", "act")):
        c = ws.cell(r, col, row[key])
        c.number_format = _NUM
        c.font = _font(bold=bold, color=color)
        c.alignment = Alignment(horizontal="right")
        if fill is not None:
            c.fill = fill


def _amount_text(item) -> str:
    parts = [f"{name} {item[key]:,.0f}" for key, name in _KEYS if item[key]]
    return " / ".join(parts) if parts else "0"


def _footnote(ws, r, text) -> int:
    c = ws.cell(r, 1, text)
    c.font = _font(size=9, italic=True, color="666666")
    return r + 1


def add_ho_sheet(wb, ho) -> None:
    """Append sheet 'HO Report' (values only) built from a build_ho_report() result."""
    ws = wb.create_sheet("HO Report")
    for r, text, size in ((1, ho["org"], 16), (2, ho["location"], 12), (3, "MD:", 12),
                          (4, f"Division/Dept.: {ho['division']}", 12)):
        c = ws.cell(r, 1, text)
        c.font = _font(size=size, bold=True, color=_BLUE)

    r = 6
    for section in ho["sections"]:
        summary = section["key"] == "summary"
        title = ws.cell(r, 1, section["title"])
        title.font = _font(bold=True)
        for col in range(1, 7):
            ws.cell(r, col).border = _LINE
        r = _header(ws, r + 1, summary, ho["period_label"])
        for row in section["rows"]:
            kind = row["type"]
            if kind == "group":
                ws.cell(r, 1, row["label"]).font = _font(bold=True)
            elif kind == "account":
                code = ws.cell(r, 1, int(row["code"]))
                code.number_format = _CODE
                code.font = _font()
                code.alignment = Alignment(horizontal="center")
                ws.cell(r, 2, row["label"]).font = _font()
                _amounts(ws, r, row, fill=_AMOUNT)
                if row.get("note"):
                    ws.cell(r, 7, row["note"]).font = _font(color="003366")
            elif summary and not row["grand"]:
                nomor = ws.cell(r, 1, row["nomor"])
                nomor.font = _font()
                nomor.alignment = Alignment(horizontal="center")
                ws.cell(r, 2, row["label"]).font = _font()
                _amounts(ws, r, row)
            else:                                    # group total or grand total
                ws.cell(r, 2 if summary else 1, row["label"]).font = _font(bold=True, color=_BLUE)
                _amounts(ws, r, row, bold=True, color=_BLUE)
                for col in range(1, 7):
                    ws.cell(r, col).border = _LINE
            r += 1
        if section["key"] == "opex":
            for u in ho["unmapped"]:
                label = f" ({u['label']})" if u["label"] else ""
                r = _footnote(ws, r, f"Tidak termasuk COA {u['coa']}{label}: {_amount_text(u)}")
        if summary:
            for m in ho["summary_missing"]:
                r = _footnote(ws, r, f"Tidak ada di ringkasan: akun {m['coa']} ({m['label']}): "
                                     f"{_amount_text(m)} (termasuk di Grand Total Opex)")
        r += 2

    for col, width in _WIDTHS.items():
        ws.column_dimensions[col].width = width
```

- [ ] **Step 4: Update `modules/management_report/exports.py`**

(a) After `from openpyxl.styles import Alignment, Font, PatternFill` add:
```python

from modules.management_report import ho_exports
```
(b) Replace the signature and first title lines of `build_cc_workbook`:
```python
def build_cc_workbook(report: dict, filters: dict = None) -> bytes:
    filters = filters or {}
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    ws["A1"] = report["cc"]
```
with
```python
def build_cc_workbook(report: dict, filters: dict = None, ho: dict = None) -> bytes:
    filters = filters or {}
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    ws["A1"] = report.get("title") or report["cc"]
```
(c) Replace
```python
    ws.freeze_panes = f"A{HEADER_ROW + 1}"

    buf = io.BytesIO()
```
with
```python
    ws.freeze_panes = f"A{HEADER_ROW + 1}"
    if ho is not None:
        ho_exports.add_ho_sheet(wb, ho)

    buf = io.BytesIO()
```
(d) Replace `def build_zip(reports: list, filters: dict = None) -> bytes:` with `def build_zip(reports: list, filters: dict = None, ho_by_cc: dict = None) -> bytes:` and replace
```python
            zf.writestr(f"{name}.xlsx", build_cc_workbook(rep, filters))
```
with
```python
            zf.writestr(f"{name}.xlsx",
                        build_cc_workbook(rep, filters, (ho_by_cc or {}).get(rep["cc"])))
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_mr_exports.py -v`
Expected: all pass (existing and 4 new).

---

### Task 5: Routes, tabs UI and HO fragment

**Files:**
- Rewrite: `modules/management_report/routes.py`
- Rewrite: `templates/management_report/index.html`
- Modify: `templates/management_report/_report_table.html`
- Create: `templates/management_report/_ho_table.html`
- Test: `tests/test_mr_routes.py` (append + 1 changed assertion), `tests/test_mr_exports.py` (1 changed assertion + 1 appended test)

**Interfaces:**
- Consumes: `ho_report.build_ho_report`, `service.get_active_meta`, `exports.build_cc_workbook(report, f, ho)`, `exports.build_zip(reports, f, ho_by_cc)`, `read_meta`.
- Produces: `GET /management-report/ho-table` (HTML fragment, same query params as `/table`; the COA param is ignored); page tabs `tab-sync`, `tab-report`, `tab-ho` with deep link `?tab=sync|report|ho` (default `report`, `sync` when there is no data yet); report title `"<org> – <CC description>"` (`"... – All"` for All Cost Center); `/export` and `/export-all` produce workbooks with sheets `Report` + `HO Report`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mr_routes.py`:

```python
HO_META = {"cc_names": {"AAA": "Alpha Unit"}, "period": "2026-08-31"}


def _seed_ho():
    svc.save_upload(2, "a.xlsb", "u", [
        mkrow(cc="AAA", coa="70105120", bgt=3.2, act=0.5, mm=1),
        mkrow(cc="BBB", coa="71000110", act=-97.5, mm=1),
    ], meta=HO_META)


def test_page_has_three_tabs_and_the_report_title_uses_the_cc_description(client):
    login(client)
    _seed_ho()
    html = client.get("/management-report/?cc=AAA").data.decode()
    for tab in ("tab-sync", "tab-report", "tab-ho"):
        assert f'data-tab="{tab}"' in html and f'id="{tab}"' in html
    assert "President Office &amp; ETF – Alpha Unit" in html
    assert "President Office &amp; ETF – All" in client.get("/management-report/?cc=ALL").data.decode()


def test_ho_fragment_shows_template_rows_and_amounts(client):
    login(client)
    _seed_ho()
    resp = client.get("/management-report/ho-table?cc=AAA")
    html = resp.data.decode()
    assert resp.status_code == 200 and "<html" not in html
    assert "Equipment Rent Expense - 3rd Party" in html and "3,200" in html
    assert "270-01-010" in html                      # GL code shown like the Excel format 000-00-000
    assert "s/d Aug" in html and "Alpha Unit" in html
    assert "Total Capex" in html and "Grand Total included Depreciation" in html


def test_ho_fragment_warns_about_coa_outside_the_template(client):
    login(client)
    _seed_ho()
    html = client.get("/management-report/ho-table?cc=BBB").data.decode()
    assert "COA di luar template HO" in html and "71000110" in html and "(97,500)" in html
    assert "COA di luar template HO" not in client.get("/management-report/ho-table?cc=AAA").data.decode()


def test_ho_fragment_login_and_empty_state(client):
    assert client.get("/management-report/ho-table?cc=ALL").status_code == 302
    login(client)
    assert "Tidak ada data" in client.get("/management-report/ho-table?cc=ALL").data.decode()


def test_ho_fragment_follows_month_filter_but_ignores_coa(client):
    login(client)
    svc.save_upload(2, "a.xlsb", "u", [mkrow(cc="AAA", coa="70105120", bgt=3.2, mm=1),
                                       mkrow(cc="AAA", coa="70106200", bgt=1.0, mm=2)])
    html = client.get("/management-report/ho-table?cc=AAA&mm=2&coa=70105120").data.decode()
    assert "Local Travel Expense" in html and "1,000" in html     # mm=2 row is counted
    html = client.get("/management-report/ho-table?cc=AAA&mm=12").data.decode()
    assert "Tidak ada data" in html
```

In `tests/test_mr_routes.py` change the assertion inside `test_export_all_cost_centers_in_one_workbook`:
```python
    assert ws["A1"].value == "All Cost Center"
```
to
```python
    assert ws["A1"].value.endswith("All")
```

In `tests/test_mr_exports.py` change, inside `test_export_route_downloads_xlsx`, the line
```python
    assert load_workbook(io.BytesIO(resp.data)).active["A1"].value == "TFKHAR"
```
to
```python
    wb = load_workbook(io.BytesIO(resp.data))
    assert wb.sheetnames == ["Report", "HO Report"]
    assert wb["Report"]["A1"].value.endswith("TFKHAR")
```
and append to `tests/test_mr_exports.py`:
```python
def test_export_all_zip_has_both_sheets_in_every_workbook(client, seeded):
    login(client)
    resp = client.get("/management-report/export-all?mm=3")
    zf = zipfile.ZipFile(io.BytesIO(resp.data))
    assert zf.namelist()
    for name in zf.namelist():
        assert load_workbook(io.BytesIO(zf.read(name))).sheetnames == ["Report", "HO Report"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_routes.py tests/test_mr_exports.py -q`
Expected: the new/changed tests FAIL (no `ho-table` route, no tab markup, single-sheet exports).

- [ ] **Step 3: Replace `modules/management_report/routes.py` with**

```python
# modules/management_report/routes.py
import io
from datetime import date

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for, Response
from flask_jwt_extended import get_jwt

from auth.middleware import is_admin, json_admin_required, jwt_html_required
from modules.management_report import exports, ho_report, service
from modules.management_report import sync as mr_sync
from modules.management_report.ho_template import load_template
from modules.management_report.parser import ParseError, read_append1, read_meta

bp = Blueprint("management_report", __name__, url_prefix="/management-report")


def _ctx():
    try:
        claims = get_jwt()
        return {
            "current_user": claims.get("username", ""),
            "current_role": claims.get("role", ""),
            "can_manage":   is_admin(claims),
            "company_id":   session.get("company_id"),
            "company_code": session.get("company_code"),
            "company_name": session.get("company_name"),
        }
    except Exception:
        return {}


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _filters() -> dict:
    return {
        "cc": request.args.get("cc") or None,
        "yy": _to_int(request.args.get("yy")),
        "mm": _to_int(request.args.get("mm")),
        "coas": [c for c in request.args.getlist("coa") if c],
    }


ALL_CC = "ALL"                    # value of the "All Cost Center" option in the CC filter
ALL_CC_LABEL = "All Cost Center"


def _resolve(company_id):
    """Filters from the query string, with the CC resolved against the active snapshot."""
    f = _filters()
    options = service.get_filter_options(company_id)
    if f["cc"] == ALL_CC or f["cc"] in options["ccs"]:
        cc = f["cc"]
    else:
        cc = options["ccs"][0] if options["ccs"] else None
    return options, {**f, "cc": cc}


def _report_title(cc, meta) -> str:
    """'<organisation> – <CC description>'; cc=None (All Cost Center) gives '... – All'."""
    desc = "All" if cc is None else (meta["cc_names"].get(cc) or cc)
    return f"{load_template()['org']} – {desc}"


def _report_for(company_id, filters):
    """Report for the resolved filters; None when there is no CC to show."""
    cc = filters["cc"]
    if cc is None:
        return None
    real = None if cc == ALL_CC else cc
    report = service.build_report(company_id, real, filters["yy"], filters["mm"], filters["coas"])
    report["title"] = _report_title(real, service.get_active_meta(company_id))
    if real is None:
        report["cc"] = ALL_CC_LABEL
    return report


def _ho_for(company_id, filters):
    cc = filters["cc"]
    real = None if cc in (None, ALL_CC) else cc
    return ho_report.build_ho_report(company_id, real, filters["yy"], filters["mm"])


@bp.route("/table")
@jwt_html_required
def table():
    """Only the Report table; the page fetches it whenever a filter changes."""
    company_id = session.get("company_id")
    if not company_id:
        return "", 400
    _, filters = _resolve(company_id)
    return render_template("management_report/_report_table.html",
                           report=_report_for(company_id, filters))


@bp.route("/ho-table")
@jwt_html_required
def ho_table():
    """Only the HO Report; the COA filter does not apply to it."""
    company_id = session.get("company_id")
    if not company_id:
        return "", 400
    _, filters = _resolve(company_id)
    return render_template("management_report/_ho_table.html", ho=_ho_for(company_id, filters))


@bp.route("/")
@jwt_html_required
def index():
    if not session.get("company_id"):
        return redirect(url_for("dashboard.select_company"))
    company_id = session["company_id"]
    options, filters = _resolve(company_id)
    return render_template(
        "management_report/index.html",
        options=options, filters=filters,
        report=_report_for(company_id, filters),
        ho=_ho_for(company_id, filters),
        default_tab="report" if options["ccs"] else "sync",
        uploads=service.list_uploads(company_id),
        last_summary=service.get_active_summary(company_id),
        active_page="management_report",
        **_ctx(),
    )


@bp.route("/sync", methods=["POST"])
@json_admin_required
def sync_excel():
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Pilih perusahaan terlebih dahulu."}), 400
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "pesan": "File belum dipilih."}), 400
    if not f.filename.lower().endswith(".xlsb"):
        return jsonify({"ok": False, "pesan": "File harus berformat .xlsb."}), 400
    data = f.read()
    try:
        result = read_append1(io.BytesIO(data))
        if not result.rows:
            raise ParseError("Tidak ada baris data yang valid di sheet Append1.")
    except ParseError as e:
        return jsonify({"ok": False, "pesan": str(e)}), 400
    meta = read_meta(io.BytesIO(data))
    out = mr_sync.sync_rows(company_id, f.filename, get_jwt().get("username", ""), result.rows,
                            meta=meta)
    if not out["changed"]:
        pesan = (f"Sudah sinkron: tidak ada perubahan sejak sync terakhir "
                 f"({out['rows']} baris).")
    else:
        s = out["summary"]
        pesan = (f"Sync selesai: {s['rows_before']} → {s['rows_after']} baris "
                 f"({result.dropped} baris dilewati).")
        if s.get("meta_changed"):
            pesan += " Deskripsi CC / periode laporan diperbarui."
    return jsonify({"ok": True, "dropped": result.dropped, "pesan": pesan, **out})


@bp.route("/uploads/<int:upload_id>/activate", methods=["POST"])
@json_admin_required
def activate(upload_id):
    company_id = session.get("company_id")
    if not company_id or not service.activate_upload(company_id, upload_id):
        return jsonify({"ok": False, "pesan": "Snapshot tidak ditemukan atau sudah dihapus."}), 404
    return jsonify({"ok": True, "pesan": "Snapshot diaktifkan."})


_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _attachment(data: bytes, filename: str, mimetype: str):
    return Response(data, mimetype=mimetype,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@bp.route("/export")
@jwt_html_required
def export_one():
    company_id = session.get("company_id")
    f = _filters()
    if not company_id or not f["cc"]:
        return jsonify({"ok": False, "pesan": "CC belum dipilih."}), 400
    real = None if f["cc"] == ALL_CC else f["cc"]
    report = service.build_report(company_id, real, f["yy"], f["mm"], f["coas"])
    if not report["has_data"]:
        return jsonify({"ok": False, "pesan": "Tidak ada data untuk CC dan filter ini."}), 404
    report["title"] = _report_title(real, service.get_active_meta(company_id))
    if real is None:
        report["cc"] = ALL_CC_LABEL
    ho = ho_report.build_ho_report(company_id, real, f["yy"], f["mm"])
    data = exports.build_cc_workbook(report, f, ho)
    return _attachment(data, f"{exports.safe_filename(f['cc'])}.xlsx", _XLSX)


@bp.route("/export-all")
@jwt_html_required
def export_all():
    company_id = session.get("company_id")
    f = _filters()
    if not company_id:
        return jsonify({"ok": False, "pesan": "Pilih perusahaan terlebih dahulu."}), 400
    meta = service.get_active_meta(company_id)
    reports, ho_by_cc = [], {}
    for cc in service.list_ccs_with_data(company_id, f["yy"], f["mm"], f["coas"]):
        report = service.build_report(company_id, cc, f["yy"], f["mm"], f["coas"])
        report["title"] = _report_title(cc, meta)
        reports.append(report)
        ho_by_cc[cc] = ho_report.build_ho_report(company_id, cc, f["yy"], f["mm"])
    if not reports:
        return jsonify({"ok": False, "pesan": "Tidak ada data untuk diexport."}), 404
    data = exports.build_zip(reports, f, ho_by_cc)
    return _attachment(data, f"Management Report {date.today().isoformat()}.zip", "application/zip")
```

- [ ] **Step 4: Update `templates/management_report/_report_table.html`**

Replace
```
<div style="margin-bottom:.5rem"><strong style="font-size:1.1rem">{{ report.cc }}</strong>
```
with
```
<div style="margin-bottom:.5rem"><strong style="font-size:1.1rem">{{ report.title or report.cc }}</strong>
```

- [ ] **Step 5: Create `templates/management_report/_ho_table.html`**

```html
{% macro h(v) %}{% if v is none or v == 0 %}-{% elif v < 0 %}({{ '{:,.0f}'.format(-v) }}){% else %}{{ '{:,.0f}'.format(v) }}{% endif %}{% endmacro %}
{% macro gl(code) %}{{ code[:-5] }}-{{ code[-5:-3] }}-{{ code[-3:] }}{% endmacro %}
{% if ho and ho.has_data %}
  {% if ho.unmapped or ho.summary_missing %}
  <div class="mr-warn">
    {% if ho.unmapped %}
    <div><strong>COA di luar template HO tidak ikut dihitung:</strong>
      {% for u in ho.unmapped %}{{ u.coa }}{% if u.label %} ({{ u.label }}){% endif %} — BGT {{ h(u.bgt) }}, PTA {{ h(u.pta) }}, ACT {{ h(u.act) }}{% if not loop.last %}; {% endif %}{% endfor %}
    </div>
    {% endif %}
    {% if ho.summary_missing %}
    <div><strong>Akun ini ikut Grand Total Opex tetapi tidak ada di ringkasan:</strong>
      {% for m in ho.summary_missing %}{{ m.coa }} ({{ m.label }}) — BGT {{ h(m.bgt) }}, PTA {{ h(m.pta) }}, ACT {{ h(m.act) }}{% if not loop.last %}; {% endif %}{% endfor %}
    </div>
    {% endif %}
  </div>
  {% endif %}
  <div class="mr-ho-head">
    <div class="mr-ho-org">{{ ho.org }}</div>
    <div>{{ ho.location }}</div>
    <div>Division/Dept.: {{ ho.division }}</div>
  </div>
  {% for s in ho.sections %}
  <div class="mr-ho-title">{{ s.title }}</div>
  <div style="overflow:auto">
  <table class="mr-table mr-ho">
    <thead>
      <tr><th>{% if s.key == 'summary' %}Nomor{% else %}GL Account{% endif %}</th>
          <th>{% if s.key == 'summary' %}Keterangan{% else %}Description{% endif %}</th>
          <th class="num">Budget</th><th class="num">PTA</th><th class="num">Actual</th><th></th></tr>
      <tr><th>{% if s.key == 'summary' %}Prakiraan{% endif %}</th><th></th>
          <th class="num">{{ ho.period_label }}</th><th class="num">{{ ho.period_label }}</th>
          <th class="num">{{ ho.period_label }}</th><th></th></tr>
    </thead>
    <tbody>
    {% for r in s.rows %}
      {% if r.type == 'group' %}
      <tr class="grp"><td colspan="6">{{ r.label }}</td></tr>
      {% elif r.type == 'account' %}
      <tr><td>{{ gl(r.code) }}</td><td>{{ r.label }}</td>
          <td class="num">{{ h(r.bgt) }}</td><td class="num">{{ h(r.pta) }}</td><td class="num">{{ h(r.act) }}</td>
          <td class="mr-note">{{ r.note or '' }}</td></tr>
      {% else %}
      <tr class="{{ 'grand' if r.grand else 'sub' }}">
        <td>{% if s.key == 'summary' %}{{ r.nomor }}{% else %}{{ r.label }}{% endif %}</td>
        <td>{% if s.key == 'summary' %}{{ r.label }}{% endif %}</td>
        <td class="num">{{ h(r.bgt) }}</td><td class="num">{{ h(r.pta) }}</td><td class="num">{{ h(r.act) }}</td><td></td>
      </tr>
      {% endif %}
    {% endfor %}
    </tbody>
  </table>
  </div>
  {% endfor %}
{% else %}
<div class="card"><p>Tidak ada data untuk filter ini.</p></div>
{% endif %}
```

- [ ] **Step 6: Replace `templates/management_report/index.html` with**

```html
{% extends "base.html" %}
{% block title %}Management Report{% endblock %}

{% block head %}
<style>
.mr-filters { display:flex; flex-wrap:wrap; gap:.75rem; align-items:flex-end; margin-bottom:1rem; }
.mr-filters label { display:block; font-size:.75rem; color:var(--sl-500); margin-bottom:.2rem; }
.mr-filters select { min-width:110px; }
.mr-table { border-collapse:collapse; width:100%; font-size:.8125rem; }
.mr-table th, .mr-table td { padding:.3rem .5rem; border-bottom:1px solid var(--sl-200); }
.mr-table th { text-align:left; background:var(--sl-50); position:sticky; top:0; }
.mr-table .num { text-align:right; font-variant-numeric:tabular-nums; }
.mr-table tr.sub td { font-weight:600; background:var(--sl-50); }
.mr-table tr.grand td { font-weight:700; border-top:2px solid var(--sl-300); }
.mr-table tr.grp td { font-weight:600; padding-top:.7rem; }
.mr-neg { color:var(--negative); }
.mr-muted { color:var(--sl-500); font-size:.8125rem; }
.mr-note { color:var(--sl-500); font-size:.75rem; }
.mr-warn { margin:0 0 .75rem; padding:.55rem .75rem; border:1px solid var(--negative); border-radius:8px;
  font-size:.8125rem; }
.mr-ho-head { margin-bottom:.5rem; line-height:1.5; }
.mr-ho-org { font-weight:700; font-size:1.1rem; }
.mr-ho-title { font-weight:600; margin:1rem 0 .35rem; }
#mr-report, #mr-ho { transition:opacity .12s; min-height:85vh; }   /* keeps the filters from jumping when a table shrinks */
#mr-report.mr-loading, #mr-ho.mr-loading { opacity:.45; }
.mr-coa { position:relative; }
.mr-coa-panel { position:absolute; z-index:30; top:calc(100% + 4px); left:0; width:240px; padding:.5rem;
  background:var(--card, #fff); border:1px solid var(--sl-300); border-radius:8px;
  box-shadow:0 8px 24px rgba(0,0,0,.18); }
.mr-coa-panel[hidden] { display:none; }
.mr-coa-panel input[type=search] { width:100%; margin-bottom:.4rem; }
.mr-coa-panel label { display:flex !important; align-items:center; gap:.4rem; margin:0; padding:.15rem 0;
  font-size:.8125rem; color:inherit; cursor:pointer; }
.mr-coa-panel input[type=checkbox] { width:auto !important; flex:none; margin:0; padding:0; }
.mr-coa-panel label[hidden] { display:none !important; }
.mr-coa-list { max-height:240px; overflow:auto; border-top:1px solid var(--sl-200); margin-top:.25rem; padding-top:.25rem; }
.mr-coa-hint { color:var(--negative); font-size:.75rem; margin-top:.25rem; }
</style>
{% endblock %}

{% block module_tabs %}
<div class="tabs" style="margin-bottom:0" title="Alt+&#8592; / Alt+&#8594; untuk pindah tab">
  <button class="tab-btn" data-tab="tab-sync">Data Sync</button>
  <button class="tab-btn" data-tab="tab-report">Report</button>
  <button class="tab-btn" data-tab="tab-ho">HO Report</button>
</div>
{% endblock %}

{% block content %}
{% macro s(v) %}{{ '{:+,.1f}'.format(v) }}{% endmacro %}
<div class="page-header"><h1>Management Report</h1></div>

<div data-tabs>

<div class="tab-panel" id="tab-sync">
<div class="card" style="margin-bottom:1rem">
  <strong>Sinkronisasi Excel</strong>
  {% set act = (uploads | selectattr('is_active') | list | first) if uploads else none %}
  <div class="mr-muted" style="margin:.25rem 0">
    {% if act %}Terakhir sync: {{ act.uploaded_at }} · {{ act.filename }} · {{ act.row_count }} baris
    {% else %}Belum pernah sync.{% endif %}
  </div>
  {% if can_manage %}
  <div style="margin:.5rem 0">
    <input type="file" id="mr-file" accept=".xlsb">
    <button class="btn btn-primary btn-sm" id="mr-sync-btn" onclick="mrSync()">Sync dari Excel</button>
    <span id="mr-sync-msg" class="mr-muted"></span>
  </div>
  {% endif %}
  {% if last_summary %}
  <div style="margin:.75rem 0; padding:.6rem .75rem; border:1px solid var(--sl-200); border-radius:8px">
    <strong>Perubahan sync terakhir</strong>
    {% if last_summary.first %}
      <div class="mr-muted">Sync pertama: {{ last_summary.rows_after }} baris dari {{ last_summary.ccs | length }} CC.</div>
    {% else %}
      <div>Baris: {{ last_summary.rows_before }} → {{ last_summary.rows_after }}
        · BGT {{ s(last_summary.delta.bgt) }} · PTA {{ s(last_summary.delta.pta) }}
        · ACT {{ s(last_summary.delta.act) }} <span class="mr-muted">(Rp Mio)</span></div>
      <div class="mr-muted">Baris laporan: {{ last_summary.lines.added }} baru,
        {{ last_summary.lines.removed }} dihapus, {{ last_summary.lines.changed }} berubah angkanya.</div>
      {% if last_summary.meta_changed %}
      <div class="mr-muted">Deskripsi CC atau periode laporan ikut berubah.</div>
      {% endif %}
      {% if last_summary.ccs %}
      <details style="margin-top:.4rem">
        <summary>CC terdampak ({{ last_summary.ccs | length }})</summary>
        <table class="mr-table" style="max-width:640px; margin-top:.3rem">
          <thead><tr><th>CC</th><th class="num">Δ BGT</th><th class="num">Δ PTA</th><th class="num">Δ ACT</th>
            <th class="num">Baru</th><th class="num">Dihapus</th><th class="num">Berubah</th></tr></thead>
          <tbody>
          {% for c in last_summary.ccs %}
            <tr><td>{{ c.cc }}</td><td class="num">{{ s(c.bgt) }}</td><td class="num">{{ s(c.pta) }}</td>
              <td class="num">{{ s(c.act) }}</td><td class="num">{{ c.added }}</td>
              <td class="num">{{ c.removed }}</td><td class="num">{{ c.changed }}</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </details>
      {% elif last_summary.meta_changed %}
      <div class="mr-muted">Angka laporan tidak berubah; hanya deskripsi CC atau periode yang berubah.</div>
      {% else %}
      <div class="mr-muted">Angka laporan tidak berubah; perbedaan hanya pada kolom COA atau periode.</div>
      {% endif %}
    {% endif %}
  </div>
  {% endif %}
  {% if uploads %}
  <div class="mr-muted" style="margin-top:.5rem">Riwayat sync</div>
  <table class="mr-table" style="max-width:760px">
    <thead><tr><th>Tanggal</th><th>File</th><th class="num">Baris</th><th>User</th><th></th></tr></thead>
    <tbody>
    {% for u in uploads %}
      <tr>
        <td>{{ u.uploaded_at }}</td><td>{{ u.filename }}</td>
        <td class="num">{{ u.row_count }}</td><td>{{ u.uploaded_by }}</td>
        <td>
          {% if u.is_active %}<strong>Aktif</strong>
          {% elif u.purged %}<span class="mr-muted">dihapus</span>
          {% elif can_manage %}
            <button class="btn btn-secondary btn-sm" onclick="mrActivate({{ u.id }})">Aktifkan</button>
          {% endif %}
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}
</div>
</div>

{% if not options.ccs %}
<div class="tab-panel" id="tab-report">
  <div class="card"><p>Belum ada data. Klik "Sync dari Excel" di tab Data Sync dan pilih file Management Report - MASTER.xlsb untuk memulai.</p></div>
</div>
<div class="tab-panel" id="tab-ho">
  <div class="card"><p>Belum ada data. Klik "Sync dari Excel" di tab Data Sync dan pilih file Management Report - MASTER.xlsb untuk memulai.</p></div>
</div>
{% else %}
<div id="mr-filter-wrap" hidden>
  <div class="mr-filters" id="mr-filters">
    <div><label for="mr-cc">CC</label>
      <select id="mr-cc">
        <option value="ALL" {% if filters.cc == 'ALL' %}selected{% endif %}>All Cost Center</option>
        {% for c in options.ccs %}<option value="{{ c }}" {% if c == filters.cc %}selected{% endif %}>{{ c }}</option>{% endfor %}
      </select></div>
    <div><label for="mr-yy">YY</label>
      <select id="mr-yy">
        <option value="">All</option>
        {% for y in options.yys %}<option value="{{ y }}" {% if y == filters.yy %}selected{% endif %}>{{ y }}</option>{% endfor %}
      </select></div>
    <div><label for="mr-mm">MM</label>
      <select id="mr-mm">
        <option value="">All</option>
        {% for m in options.mms %}<option value="{{ m }}" {% if m == filters.mm %}selected{% endif %}>{{ m }}</option>{% endfor %}
      </select></div>
    <div class="mr-coa" id="mr-coa"><label>COA</label>
      <button type="button" class="btn btn-secondary btn-sm" id="mr-coa-btn">COA: All ▾</button>
      <div class="mr-coa-panel" id="mr-coa-panel" hidden>
        <input type="search" id="mr-coa-search" placeholder="Cari COA">
        <label><input type="checkbox" id="mr-coa-all"> (Pilih semua)</label>
        <div class="mr-coa-list">
          {% for c in options.coas %}
          <label data-coa="{{ c }}"><input type="checkbox" class="mr-coa-item" value="{{ c }}" {% if not filters.coas or c in filters.coas %}checked{% endif %}> {{ c }}</label>
          {% endfor %}
        </div>
        <div class="mr-coa-hint" id="mr-coa-hint" hidden>Pilih minimal satu COA.</div>
      </div></div>
    <div>
      <a class="btn btn-secondary btn-sm" id="mr-export-one"
         href="{{ url_for('management_report.export_one', cc=filters.cc, yy=filters.yy, mm=filters.mm, coa=filters.coas) }}">Export CC ini</a>
      <a class="btn btn-secondary btn-sm" id="mr-export-all"
         href="{{ url_for('management_report.export_all', yy=filters.yy, mm=filters.mm, coa=filters.coas) }}">Export semua CC (ZIP)</a>
    </div>
  </div>
</div>

<div class="tab-panel" id="tab-report">
  <div id="mr-report">{% include "management_report/_report_table.html" %}</div>
</div>
<div class="tab-panel" id="tab-ho">
  <div id="mr-ho">{% include "management_report/_ho_table.html" %}</div>
</div>
{% endif %}

</div>
{% endblock %}

{% block scripts %}
<script>
/* Choose the tab before the app's initTabs() runs: Report when there is data, otherwise Data Sync. */
(function () {
  const u = new URL(location.href);
  if (!u.searchParams.get('tab')) { u.searchParams.set('tab', {{ default_tab | tojson }}); history.replaceState(null, '', u); }
})();

async function mrSync() {
  const f = document.getElementById('mr-file').files[0];
  const msg = document.getElementById('mr-sync-msg');
  if (!f) { msg.textContent = 'Pilih file master .xlsb dulu.'; return; }
  const btn = document.getElementById('mr-sync-btn');
  btn.disabled = true; msg.textContent = 'Menyinkronkan...';
  const fd = new FormData(); fd.append('file', f);
  try {
    const r = await fetch('/management-report/sync', {method: 'POST', body: fd, credentials: 'same-origin'});
    const j = await r.json();
    msg.textContent = j.pesan || (r.ok ? 'Selesai.' : 'Gagal.');
    if (j.ok && j.changed) setTimeout(() => location.reload(), 800);
  } catch (e) { msg.textContent = 'Gagal sync: ' + e; }
  btn.disabled = false;
}
async function mrActivate(id) {
  try {
    const r = await fetch('/management-report/uploads/' + id + '/activate', {method: 'POST', credentials: 'same-origin'});
    const j = await r.json();
    if (j.ok) location.reload(); else alert(j.pesan);
  } catch (e) { alert('Gagal: ' + e); }
}

/* Filters: any change refetches only the visible tab's table (no page reload). */
(function () {
  const wrap = document.getElementById('mr-filter-wrap');
  if (!wrap) return;                                   // no data synced yet
  const cc = document.getElementById('mr-cc'), yy = document.getElementById('mr-yy'),
        mm = document.getElementById('mr-mm');
  const coaBox = document.getElementById('mr-coa'), btn = document.getElementById('mr-coa-btn'),
        panel = document.getElementById('mr-coa-panel'), search = document.getElementById('mr-coa-search'),
        allBox = document.getElementById('mr-coa-all'), hint = document.getElementById('mr-coa-hint');
  const items = Array.from(document.querySelectorAll('.mr-coa-item'));
  const panes = {report: document.getElementById('mr-report'), ho: document.getElementById('mr-ho')};
  const exportOne = document.getElementById('mr-export-one'), exportAll = document.getElementById('mr-export-all');
  const stale = {report: false, ho: false};            // a tab not shown while a filter changed
  let tab = 'report', timer = null, seq = 0;

  const selected = () => items.filter(i => i.checked).map(i => i.value);

  function query(withCc, withCoa) {
    const p = new URLSearchParams();
    if (withCc) p.set('cc', cc.value);
    if (yy.value) p.set('yy', yy.value);
    if (mm.value) p.set('mm', mm.value);
    const sel = selected();
    if (withCoa && sel.length && sel.length < items.length) sel.forEach(c => p.append('coa', c));
    return p.toString();
  }

  function syncCoaUi() {
    const n = selected().length;
    btn.textContent = 'COA: ' + (n === items.length ? 'All' : n + ' dipilih') + ' ▾';
    const visible = items.filter(i => !i.closest('label').hidden);
    const ticked = visible.filter(i => i.checked).length;
    allBox.checked = visible.length > 0 && ticked === visible.length;
    allBox.indeterminate = ticked > 0 && ticked < visible.length;
    hint.hidden = n > 0;
  }

  function refresh() {
    if (tab !== 'report' && tab !== 'ho') return;
    clearTimeout(timer);
    timer = setTimeout(async () => {
      if (selected().length === 0) return;             // like Excel: at least one item must stay ticked
      const mine = ++seq, name = tab, pane = panes[name];
      const q = query(true, name === 'report');
      pane.classList.add('mr-loading');
      try {
        const r = await fetch('/management-report/' + (name === 'report' ? 'table?' : 'ho-table?') + q,
                              {credentials: 'same-origin'});
        if (r.redirected || !r.ok) { location.reload(); return; }   // session expired
        const html = await r.text();
        if (mine !== seq) return;                      // a newer filter change is already running
        pane.innerHTML = html;
        stale[name] = false;
        history.replaceState(null, '', '?' + query(true, true) + '&tab=' + tab);
        exportOne.href = '/management-report/export?' + query(true, true);
        exportAll.href = '/management-report/export-all?' + query(false, true);
      } catch (e) {
        const box = document.createElement('div');
        box.className = 'card';
        box.textContent = 'Gagal memuat laporan: ' + e;
        pane.replaceChildren(box);
      } finally {
        if (mine === seq) pane.classList.remove('mr-loading');
      }
    }, 120);
  }

  function filtersChanged() { stale.report = stale.ho = true; refresh(); }

  function showTab(name) {                             // runs for every tab click, incl. the initial one
    tab = name;
    wrap.hidden = name === 'sync';
    coaBox.hidden = name !== 'report';
    if ((name === 'report' || name === 'ho') && stale[name]) refresh();
  }
  document.querySelectorAll('.tabs .tab-btn').forEach(b =>
    b.addEventListener('click', () => showTab(b.dataset.tab.replace(/^tab-/, ''))));

  [cc, yy, mm].forEach(el => el.addEventListener('change', filtersChanged));
  btn.addEventListener('click', () => { panel.hidden = !panel.hidden; if (!panel.hidden) search.focus(); });
  document.addEventListener('click', e => { if (!panel.hidden && !coaBox.contains(e.target)) panel.hidden = true; });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') panel.hidden = true; });
  search.addEventListener('input', () => {
    const q = search.value.trim().toLowerCase();
    items.forEach(i => { i.closest('label').hidden = q !== '' && !i.value.toLowerCase().includes(q); });
    syncCoaUi();
  });
  allBox.addEventListener('change', () => {            // acts on the items currently shown (as in Excel)
    items.filter(i => !i.closest('label').hidden).forEach(i => { i.checked = allBox.checked; });
    syncCoaUi(); filtersChanged();
  });
  items.forEach(i => i.addEventListener('change', () => { syncCoaUi(); filtersChanged(); }));
  syncCoaUi();
})();
</script>
{% endblock %}
```

- [ ] **Step 7: Run the tests**

Run: `python -m pytest tests/test_mr_routes.py tests/test_mr_exports.py tests/test_mr_meta.py tests/test_mr_ho_report.py tests/test_mr_ho_template.py tests/test_mr_service.py tests/test_mr_report.py tests/test_mr_parser.py tests/test_mr_sync.py tests/test_mr_reconciliation.py tests/test_dashboard.py -q`
Expected: all pass.

---

### Task 6: Verification against Excel and in the browser

**Files:**
- Create: `scripts/crosscheck_ho_with_excel.py`
- (no production code changes expected; fix only what this task proves wrong)

- [ ] **Step 1: Create `scripts/crosscheck_ho_with_excel.py`**

```python
"""Compare Flow's HO Report with Excel's own sheet 'BGT HO Report per CC' for chosen cost centers.

    python scripts/crosscheck_ho_with_excel.py "C:\\path\\Management Report - MASTER.xlsb" POCFAD POOFFM TFEDIR

Excel drives its CC slicer on a copy of the workbook; nothing is saved. Prints one line per CC.
"""
import collections
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import win32com.client                                             # noqa: E402

from modules.management_report.ho_report import compute_ho        # noqa: E402
from modules.management_report.ho_template import load_template   # noqa: E402
from modules.management_report.parser import read_append1         # noqa: E402


def flow_values(rows, cc):
    agg = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in rows:
        if cc is None or r["cc"] == cc:
            a = agg[r["coa"]]
            a[0] += r["bgt"]
            a[1] += r["pta"]
            a[2] += r["act"]
    out = compute_ho(load_template(), dict(agg))
    return {r["id"]: (r["bgt"], r["pta"], r["act"])
            for s in out["sections"] for r in s["rows"] if "bgt" in r}


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    master, ccs = argv[1], argv[2:]
    tmp = os.path.join(tempfile.mkdtemp(), "m.xlsb")
    shutil.copyfile(master, tmp)
    with open(tmp, "rb") as f:
        rows = read_append1(io.BytesIO(f.read())).rows
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.EnableEvents = False
    xl.AutomationSecurity = 3
    wb = xl.Workbooks.Open(tmp, 0, True)
    bad_total = 0
    try:
        ws = wb.Worksheets.Item("BGT HO Report per CC")
        slicer = wb.SlicerCaches.Item("Slicer_CC")
        for cc in ccs:
            slicer.VisibleSlicerItemsList = [f"[Append1__2].[CC].&[{cc}]"]
            xl.Calculate()
            flow = flow_values(rows, cc)
            bad = []
            for rid, vals in flow.items():
                excel = [float(ws.Cells(rid, col).Value2 or 0) for col in (4, 5, 6)]
                if any(abs(a - b) > 1e-3 for a, b in zip(vals, excel)):
                    bad.append((rid, vals, excel))
            bad_total += len(bad)
            print(f"{cc}: {len(flow)} rows compared, {len(bad)} mismatches")
            for rid, vals, excel in bad[:5]:
                print("   row", rid, "flow", vals, "excel", excel)
    finally:
        wb.Close(False)
        xl.Quit()
    sys.exit(1 if bad_total else 0)


if __name__ == "__main__":
    main(sys.argv)
```

- [ ] **Step 2: Run the cross-check on cost centers that exercise every special case**

Run: `python scripts/crosscheck_ho_with_excel.py "C:\Users\25010160\Downloads\Management Report - MASTER.xlsb" TFKHAR POCFAD POOFFM TFEDIR POSENG`
Expected: every line ends with `0 mismatches` (POCFAD = COA outside the template, POOFFM = summary gap, TFEDIR = another unmapped COA, POSENG = the CC with the most rows). Exit code 0. If the slicer cannot be driven (COM error), report that and skip this step; it must not be forced.

- [ ] **Step 3: Full MR regression**

Run: `python -m pytest tests/test_mr_routes.py tests/test_mr_exports.py tests/test_mr_meta.py tests/test_mr_ho_report.py tests/test_mr_ho_template.py tests/test_mr_service.py tests/test_mr_report.py tests/test_mr_parser.py tests/test_mr_sync.py tests/test_mr_reconciliation.py tests/test_dashboard.py -q`
Expected: all pass.

- [ ] **Step 4: Browser check (controller)**

The controller starts a throwaway instance (temp database seeded with the real master workbook through `sync_rows`, `read_meta` included, port 8090), logs in with the project's seed credentials and verifies in the in-app browser: default tab is Report; tabs switch without reload and the URL gets `?tab=`; the filter bar is hidden on Data Sync and the COA control hidden on HO Report; changing CC/MM on the HO tab refreshes it in place and marks the Report tab stale; All Cost Center works on both tabs; the HO warnings appear for POCFAD (71000110) and POOFFM (70102114); "Export CC ini" downloads a workbook with the sheets `Report` and `HO Report`; the Data Sync tab shows the sync card and history. The controller then stops the throwaway server and deletes its database.

- [ ] **Step 5: Report to the user**

State test results, the cross-check output, the browser findings, and that the Excel template itself has gaps that Flow reproduces and flags: account `70102114` is in no summary line (summary total lower than the Opex grand total for CCs with data there); `70101300` and `70114949` are listed but in no group total; COAs `71000110` and `70004112` are not in the template. Remind that the server must be restarted (templates are cached) and that nothing was committed.
