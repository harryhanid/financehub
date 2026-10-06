# Management Report: Append Data Table and Raw-Data Sheet - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the whole synced Append table (paged, filterable, exportable) at the bottom of the Data Sync tab, and add a third sheet `Append` with the raw rows to every per-CC export.

**Architecture:** One service query (`query_append`) feeds three consumers: the Data Sync table fragment, the standalone Append export, and the third sheet of the per-CC / ZIP exports. Export code is shared through `exports.add_append_sheet`.

**Tech Stack:** Flask, SQLite (`database.get_conn`), `openpyxl`, pytest. Front end: the existing fragment-fetch pattern of the module (vanilla JS).

Spec: `docs/superpowers/specs/2026-10-06-management-report-append-data-design.md`

## Global Constraints

- Work in `C:\Financehub\app`; run pytest from there (`python -m pytest ...`). Paths below are relative to it unless they start with `docs/`.
- **No git operations** (`add`, `commit`, `stash`, `checkout`, ...) in `C:\Financehub`: the tree holds the user's uncommitted work. Use the Edit tool for existing files and the Write tool for new files (not Python/shell scripts that rewrite files).
- Every query is filtered by `company_id` through the active snapshot. Append columns, in order: `coa, mm, yy, cc, category, activity, description, pta, custom, mm1, act, bgt` (headers `COA, MM, YY, CC, Category, Activity, Description, PTA, Custom, MM.1, ACT, BGT`).
- Sheet 3 of the per-CC export follows the Report filters (CC, YY, MM, COA); the Data Sync table and its export follow only CC + search. Page size 100.
- Screen numbers use the module's Indonesian filters (`mr_num`, `mr_pct`, `mr_amt` from `formatting.py`). Excel cells stay numeric.
- All existing `tests/test_mr_*.py` and `tests/test_dashboard.py` must keep passing, except the two assertions Task 3 changes explicitly. Known unrelated failure in the full suite: `tests/test_sponsorship_routes.py::test_input_page_has_cat1_search_and_lembaga_datalist`; run only the module's tests.
- Templates are cached by a running server; pytest builds a fresh app each time.
- Sample master workbook for real-data checks: `C:\Users\25010160\Downloads\Management Report - MASTER.xlsb` (env `MR_SAMPLE_XLSB` overrides; tests that use it skip when missing).

## File Structure

| File | Responsibility |
|---|---|
| `modules/management_report/service.py` | (modify) `query_append` |
| `modules/management_report/exports.py` | (modify) `add_append_sheet`, `build_append_workbook`, third sheet in `build_cc_workbook` / `build_zip` |
| `modules/management_report/routes.py` | (modify) `/append-table`, `/append/export`, exports pass Append rows |
| `templates/management_report/_append_table.html` | (create) table + pager fragment |
| `templates/management_report/index.html` | (modify) Data Append card in the Data Sync tab + JS + CSS |
| `tests/test_mr_append.py` | (create) service tests |
| `tests/test_mr_exports.py`, `tests/test_mr_routes.py` | (modify) |

---

### Task 1: `query_append` in the service

**Files:**
- Modify: `modules/management_report/service.py` (append at the end)
- Test: `tests/test_mr_append.py`

**Interfaces:**
- Produces: `service.query_append(company_id, cc=None, yy=None, mm=None, coas=None, q=None, limit=None, offset=0) -> {"rows": [dict], "total": int}`. Rows are dicts with the 12 Append column names; order = insertion order (`id`); `total` counts all rows passing the filters (ignores `limit`/`offset`); no active snapshot -> `{"rows": [], "total": 0}`; `q` = case-insensitive substring over `coa, category, activity, description` with `%`, `_`, `\` matched literally; `coas` empty/None = no COA filter.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_mr_append.py`:

```python
from modules.management_report import service as svc
from tests.test_mr_service import mkrow

COLUMNS = ["coa", "mm", "yy", "cc", "category", "activity", "description",
           "pta", "custom", "mm1", "act", "bgt"]


def seed(rows, company=1):
    svc.save_upload(company, "m.xlsb", "u", rows)


def rows3():
    return [
        mkrow(cc="AAA", coa="111", mm=1, yy=26, description="Alpha rent", activity="Ops",
              category="01 - Rental", bgt=1.0),
        mkrow(cc="AAA", coa="222", mm=2, yy=26, description="Beta travel", bgt=2.0),
        mkrow(cc="BBB", coa="111", mm=2, yy=25, description="100% donation_x", bgt=3.0),
    ]


def test_all_rows_come_back_in_insertion_order_with_the_append_columns():
    seed(rows3())
    res = svc.query_append(1)
    assert res["total"] == 3
    assert [r["description"] for r in res["rows"]] == ["Alpha rent", "Beta travel", "100% donation_x"]
    assert list(res["rows"][0]) == COLUMNS
    assert res["rows"][0]["bgt"] == 1.0 and res["rows"][0]["cc"] == "AAA"


def test_filters_cc_year_month_and_coa():
    seed(rows3())
    assert svc.query_append(1, cc="AAA")["total"] == 2
    assert svc.query_append(1, yy=25)["total"] == 1
    assert svc.query_append(1, mm=2)["total"] == 2
    assert svc.query_append(1, coas=["111"])["total"] == 2
    assert svc.query_append(1, coas=["111", "222"])["total"] == 3
    assert svc.query_append(1, coas=[])["total"] == 3                  # empty = no COA filter
    assert svc.query_append(1, cc="AAA", mm=2, coas=["222"])["total"] == 1
    assert svc.query_append(1, cc="NOPE")["rows"] == []


def test_search_is_case_insensitive_over_text_columns_and_wildcards_are_literal():
    seed(rows3())
    q = lambda text: [r["description"] for r in svc.query_append(1, q=text)["rows"]]
    assert q("RENT") == ["Alpha rent"]
    assert q("beta") == ["Beta travel"]
    assert q("01 - rental") == ["Alpha rent"]                         # category
    assert q("ops") == ["Alpha rent"]                                 # activity
    assert len(q("111")) == 2                                         # coa
    assert q("%") == ["100% donation_x"]                              # literal percent sign
    assert q("_x") == ["100% donation_x"]                             # literal underscore
    assert q("zzz") == []


def test_paging_keeps_the_total_of_the_whole_filter():
    seed([mkrow(cc="AAA", description=f"row {i}") for i in range(5)])
    first = svc.query_append(1, limit=2, offset=0)
    assert first["total"] == 5 and [r["description"] for r in first["rows"]] == ["row 0", "row 1"]
    last = svc.query_append(1, limit=2, offset=4)
    assert last["total"] == 5 and [r["description"] for r in last["rows"]] == ["row 4"]
    assert svc.query_append(1, limit=2, offset=10)["rows"] == []


def test_no_snapshot_and_company_isolation():
    assert svc.query_append(1) == {"rows": [], "total": 0}
    seed(rows3(), company=2)
    assert svc.query_append(1) == {"rows": [], "total": 0}
    assert svc.query_append(2)["total"] == 3
    seed([mkrow(cc="NEW", description="only in the new snapshot")], company=2)
    assert [r["cc"] for r in svc.query_append(2)["rows"]] == ["NEW"]   # active snapshot only
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_append.py -q`
Expected: 5 FAILED with `AttributeError: module ... has no attribute 'query_append'`.

- [ ] **Step 3: Implement**

Append to the end of `modules/management_report/service.py`:

```python
_APPEND_COLS = ("coa", "mm", "yy", "cc", "category", "activity", "description",
                "pta", "custom", "mm1", "act", "bgt")


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def query_append(company_id: int, cc=None, yy=None, mm=None, coas=None, q=None,
                 limit=None, offset=0) -> dict:
    """Rows of the active snapshot in sheet-Append1 order, plus the total for the filter.

    `q` is a case-insensitive substring over coa, category, activity and description;
    `limit=None` returns every row that passes the filters."""
    uid = get_active_upload_id(company_id)
    if uid is None:
        return {"rows": [], "total": 0}
    where, params = _where(uid, cc, yy, mm, coas)
    if q:
        like = f"%{_like_escape(q.lower())}%"
        where += (" AND (LOWER(coa) LIKE ? ESCAPE '\\' OR LOWER(category) LIKE ? ESCAPE '\\'"
                  " OR LOWER(activity) LIKE ? ESCAPE '\\' OR LOWER(description) LIKE ? ESCAPE '\\')")
        params = params + [like] * 4
    conn = get_conn()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM mr_append WHERE {where}", params).fetchone()[0]
        sql = f"SELECT {', '.join(_APPEND_COLS)} FROM mr_append WHERE {where} ORDER BY id"
        args = list(params)
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            args += [limit, offset]
        rows = [dict(r) for r in conn.execute(sql, args).fetchall()]
        return {"rows": rows, "total": total}
    finally:
        conn.close()
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_mr_append.py tests/test_mr_service.py tests/test_mr_report.py -q`
Expected: all pass.

---

### Task 2: Append sheet in the exports

**Files:**
- Modify: `modules/management_report/exports.py`
- Test: `tests/test_mr_exports.py` (append)

**Interfaces:**
- Consumes: rows from `service.query_append(...)["rows"]` (Task 1).
- Produces: `exports.APPEND_HEADERS` (list of 12 headers); `exports.add_append_sheet(wb, rows, name="Append")`; `exports.build_append_workbook(rows) -> bytes` (workbook with only sheet `Append`); `exports.build_cc_workbook(report, filters=None, ho=None, append_rows=None)` adds sheet `Append` last when `append_rows is not None`; `exports.build_zip(reports, filters=None, ho_by_cc=None, append_by_cc=None)` passes `append_by_cc.get(report["cc"])`.
- Sheet layout: row 1 headers (bold, light-grey fill `E2E8F0`, centered); data from row 2; `COA, MM, YY, MM.1` written as integers (COA stays text when not all digits), `PTA/ACT/BGT` numbers with format `#,##0.0##`, other columns text; `None` stays an empty cell; freeze panes `A2`; auto-filter over the used range (`A1:L<last row>`); widths A 11, B 5, C 5, D 14, E 36, F 24, G 70, H 12, I 8, J 6, K 12, L 12.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mr_exports.py` (add `from modules.management_report.exports import APPEND_HEADERS, build_append_workbook` to the imports at the top of the file):

```python
def _append_rows(cc, **kw):
    return svc.query_append(2, cc, **kw)["rows"]


def test_workbook_gets_an_append_sheet_with_the_raw_rows(seeded):
    rep = svc.build_report(2, "TFKHAR")
    rows = _append_rows("TFKHAR")
    wb = load_workbook(io.BytesIO(build_cc_workbook(rep, {}, None, rows)))
    assert wb.sheetnames == ["Report", "Append"]
    ws = wb["Append"]
    assert [c.value for c in ws[1]] == APPEND_HEADERS
    assert ws.max_row == 1 + len(rows) == 3
    assert ws.freeze_panes == "A2" and ws.auto_filter.ref == "A1:L3"
    bgt = APPEND_HEADERS.index("BGT") + 1
    assert sum(ws.cell(r, bgt).value for r in range(2, ws.max_row + 1)) == \
        pytest.approx(rep["grand"]["bgt"])                      # reconciles with sheet Report
    assert ws.cell(2, 1).value == 70105120                      # COA as a number
    assert ws.cell(2, bgt).number_format == "#,##0.0##"
    assert ws.cell(2, APPEND_HEADERS.index("Description") + 1).value == "Rent"


def test_append_sheet_comes_after_the_ho_sheet(ho_seeded):
    rep = svc.build_report(2, "AAA")
    wb = load_workbook(io.BytesIO(
        build_cc_workbook(rep, {}, hr.build_ho_report(2, "AAA"), _append_rows("AAA"))))
    assert wb.sheetnames == ["Report", "HO Report", "Append"]
    assert wb["Append"].max_row == 1 + 3


def test_append_sheet_values_and_empty_cells(seeded):
    rows = _append_rows("TFKHAR")[:1]
    rows[0].update(coa="70105120A", mm=None, description=None)
    ws = load_workbook(io.BytesIO(build_cc_workbook(svc.build_report(2, "TFKHAR"), {}, None, rows)))["Append"]
    assert ws.cell(2, 1).value == "70105120A"                   # not all digits: kept as text
    assert ws.cell(2, 2).value is None                          # MM empty
    assert ws.cell(2, APPEND_HEADERS.index("Description") + 1).value is None


def test_workbook_without_append_rows_has_no_append_sheet(seeded):
    wb = load_workbook(io.BytesIO(build_cc_workbook(svc.build_report(2, "TFKHAR"))))
    assert "Append" not in wb.sheetnames


def test_zip_gives_every_cc_its_own_append_rows(seeded):
    reps = [svc.build_report(2, cc) for cc in ("TFKHAR", "POSKHU - AR")]
    by_cc = {cc: _append_rows(cc) for cc in ("TFKHAR", "POSKHU - AR")}
    zf = zipfile.ZipFile(io.BytesIO(build_zip(reps, {}, None, by_cc)))
    counts = {}
    for name in zf.namelist():
        wb = load_workbook(io.BytesIO(zf.read(name)))
        assert wb.sheetnames == ["Report", "Append"]
        counts[name] = wb["Append"].max_row - 1
    assert counts == {"TFKHAR.xlsx": 2, "POSKHU - AR.xlsx": 1}


def test_standalone_append_workbook_has_only_the_append_sheet(seeded):
    wb = load_workbook(io.BytesIO(build_append_workbook(_append_rows(None))))
    assert wb.sheetnames == ["Append"] and wb["Append"].max_row == 1 + 4
```

(`seeded` rows: 2 x TFKHAR, 1 x `POSKHU - AR`, 1 x EMPTYCC = 4 rows; `ho_seeded` has 3 AAA rows; both fixtures already exist in this file.)

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_exports.py -q`
Expected: collection ERROR (`cannot import name 'APPEND_HEADERS'`).

- [ ] **Step 3: Implement**

In `modules/management_report/exports.py`:

(a) After the `_WIDTHS = {...}` block (before `def safe_filename`) add:
```python
APPEND_HEADERS = ["COA", "MM", "YY", "CC", "Category", "Activity", "Description",
                  "PTA", "Custom", "MM.1", "ACT", "BGT"]
_APPEND_KEYS = ["coa", "mm", "yy", "cc", "category", "activity", "description",
                "pta", "custom", "mm1", "act", "bgt"]
_APPEND_WIDTHS = {"A": 11, "B": 5, "C": 5, "D": 14, "E": 36, "F": 24, "G": 70,
                  "H": 12, "I": 8, "J": 6, "K": 12, "L": 12}
_APPEND_NUM_FMT = "#,##0.0##"
```
(b) Directly above `def build_cc_workbook` add:
```python
def _append_value(key: str, value):
    if value is None:
        return None
    if key == "coa":
        return int(value) if str(value).isdigit() else value
    return value


def add_append_sheet(wb, rows: list, name: str = "Append"):
    """Raw Append rows as a plain table: header row, one row per Append line, values only."""
    ws = wb.create_sheet(name)
    for col, header in enumerate(APPEND_HEADERS, start=1):
        c = ws.cell(1, col, header)
        c.font = _BOLD
        c.fill = _FILL_HEAD
        c.alignment = Alignment(horizontal="center")
    for r, row in enumerate(rows, start=2):
        for col, key in enumerate(_APPEND_KEYS, start=1):
            c = ws.cell(r, col, _append_value(key, row.get(key)))
            if key in ("pta", "act", "bgt"):
                c.number_format = _APPEND_NUM_FMT
    for col, width in _APPEND_WIDTHS.items():
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:L{max(len(rows) + 1, 2)}"
    return ws


def build_append_workbook(rows: list) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    add_append_sheet(wb, rows)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


```
(c) Replace `def build_cc_workbook(report: dict, filters: dict = None, ho: dict = None) -> bytes:` with
`def build_cc_workbook(report: dict, filters: dict = None, ho: dict = None, append_rows: list = None) -> bytes:`
(d) Replace
```python
    if ho is not None:
        ho_exports.add_ho_sheet(wb, ho)
```
with
```python
    if ho is not None:
        ho_exports.add_ho_sheet(wb, ho)
    if append_rows is not None:
        add_append_sheet(wb, append_rows)
```
(e) Replace `def build_zip(reports: list, filters: dict = None, ho_by_cc: dict = None) -> bytes:` with `def build_zip(reports: list, filters: dict = None, ho_by_cc: dict = None, append_by_cc: dict = None) -> bytes:` and replace
```python
            zf.writestr(f"{name}.xlsx",
                        build_cc_workbook(rep, filters, (ho_by_cc or {}).get(rep["cc"])))
```
with
```python
            zf.writestr(f"{name}.xlsx",
                        build_cc_workbook(rep, filters, (ho_by_cc or {}).get(rep["cc"]),
                                          (append_by_cc or {}).get(rep["cc"])))
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_mr_exports.py tests/test_mr_append.py -q`
Expected: all pass (existing + 6 new).

---

### Task 3: Routes, Data Sync table and export wiring

**Files:**
- Modify: `modules/management_report/routes.py`
- Create: `templates/management_report/_append_table.html`
- Modify: `templates/management_report/index.html`
- Test: `tests/test_mr_routes.py` (append + 1 changed assertion), `tests/test_mr_exports.py` (1 changed assertion + 1 appended test)

**Interfaces:**
- Consumes: `service.query_append`, `exports.build_append_workbook`, `exports.build_cc_workbook(..., append_rows)`, `exports.build_zip(..., append_by_cc)`.
- Produces: `GET /management-report/append-table?cc=&q=&page=` (HTML fragment; `page` 1-based, clamped; unknown/`ALL` cc = all); `GET /management-report/append/export?cc=&q=` (`Append.xlsx`, 404 JSON when no rows); `/export` and `/export-all` now also write the `Append` sheet (rows follow the Report filters: CC, YY, MM, COA).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mr_routes.py` (it already imports `io`, `svc`, `mkrow`, `login`):

```python
# ---------- Data Append (Data Sync tab) ----------

def _seed_append():
    rows = [mkrow(cc="AAA", coa="70105120", description=f"row {i}", mm=1, bgt=1.5)
            for i in range(150)]
    rows.append(mkrow(cc="BBB", coa="70106200", description="travel 100% <b>x</b>", mm=2, bgt=2.0))
    svc.save_upload(2, "a.xlsb", "u", rows)


def test_data_sync_tab_has_the_append_section(client):
    login(client)
    _seed_append()
    html = client.get("/management-report/?tab=sync").data.decode()
    assert 'id="mr-append"' in html and 'id="mr-append-cc"' in html and 'id="mr-append-q"' in html
    assert "Export Append (Excel)" in html


def test_append_fragment_pages_filters_and_escapes(client):
    login(client)
    _seed_append()
    get = lambda qs: client.get("/management-report/append-table" + qs).data.decode()
    html = get("")
    assert "<html" not in html and "151 baris" in html and "Halaman 1 dari 2" in html
    assert "row 0<" in html and "row 99<" in html and "row 100<" not in html
    page2 = get("?page=2")
    assert "Halaman 2 dari 2" in page2 and "row 149<" in page2 and "row 0<" not in page2
    assert "Halaman 2 dari 2" in get("?page=99")                     # clamped
    assert "Halaman 1 dari 2" in get("?page=abc") and "Halaman 1 dari 2" in get("?page=0")
    by_cc = get("?cc=BBB")
    assert ">1 baris<" in by_cc and "travel 100%" in by_cc
    assert "151 baris" in get("?cc=NOPE")                            # unknown CC = all
    assert "151 baris" in get("?cc=ALL")
    assert ">1 baris<" in get("?q=travel") and ">1 baris<" in get("?q=%25")   # '%' matches literally
    assert "&lt;b&gt;x&lt;/b&gt;" in by_cc and "<b>x</b>" not in by_cc    # escaped
    assert "Tidak ada baris" in get("?q=zzz")


def test_append_fragment_empty_state_and_login(client):
    assert client.get("/management-report/append-table").status_code == 302
    login(client)
    assert "Belum ada data" in client.get("/management-report/append-table").data.decode()


def test_append_export_downloads_the_filtered_rows(client):
    from openpyxl import load_workbook
    login(client)
    _seed_append()
    resp = client.get("/management-report/append/export")
    assert resp.status_code == 200 and "Append.xlsx" in resp.headers["Content-Disposition"]
    wb = load_workbook(io.BytesIO(resp.data))
    assert wb.sheetnames == ["Append"] and wb["Append"].max_row == 1 + 151
    only_b = load_workbook(io.BytesIO(client.get("/management-report/append/export?cc=BBB").data))
    assert only_b["Append"].max_row == 2
    assert load_workbook(io.BytesIO(
        client.get("/management-report/append/export?q=travel").data))["Append"].max_row == 2
    assert client.get("/management-report/append/export?q=zzz").status_code == 404


def test_append_export_login_and_empty_snapshot(client):
    assert client.get("/management-report/append/export").status_code == 302
    login(client)
    assert client.get("/management-report/append/export").status_code == 404


def test_report_export_has_an_append_sheet_that_follows_the_report_filters(client):
    from openpyxl import load_workbook
    login(client)
    svc.save_upload(2, "a.xlsb", "u", [
        mkrow(cc="AAA", coa="111", mm=1, bgt=1.0), mkrow(cc="AAA", coa="222", mm=2, bgt=2.0),
        mkrow(cc="BBB", coa="111", mm=2, bgt=4.0)])
    wb = load_workbook(io.BytesIO(client.get("/management-report/export?cc=AAA").data))
    assert wb.sheetnames == ["Report", "HO Report", "Append"]
    assert wb["Append"].max_row == 1 + 2
    wb = load_workbook(io.BytesIO(client.get("/management-report/export?cc=ALL&mm=2&coa=111").data))
    ws = wb["Append"]
    assert ws.max_row == 1 + 1 and ws.cell(2, 4).value == "BBB"          # CC, MM and COA filters apply
    all_ccs = load_workbook(io.BytesIO(client.get("/management-report/export?cc=ALL").data))["Append"]
    assert all_ccs.max_row == 1 + 3
```

In `tests/test_mr_routes.py`, in `test_export_all_cost_centers_in_one_workbook`, nothing changes. In `tests/test_mr_exports.py`:
- in `test_export_route_downloads_xlsx` change `assert wb.sheetnames == ["Report", "HO Report"]` to `assert wb.sheetnames == ["Report", "HO Report", "Append"]`;
- in `test_export_all_zip_has_both_sheets_in_every_workbook` change `assert load_workbook(io.BytesIO(zf.read(name))).sheetnames == ["Report", "HO Report"]` to `assert load_workbook(io.BytesIO(zf.read(name))).sheetnames == ["Report", "HO Report", "Append"]`.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mr_routes.py tests/test_mr_exports.py -q`
Expected: the new tests and the two changed assertions FAIL (no `append-table` route, no Append sheet in the routes' exports); everything else passes.

- [ ] **Step 3: Routes**

In `modules/management_report/routes.py`:

(a) Add this block directly above `@bp.route("/")` (the `index` route):
```python
APPEND_PAGE_SIZE = 100


def _append_args(company_id):
    """cc, q, page for the Data Sync table; an unknown or ALL cc means all cost centers."""
    cc = request.args.get("cc") or None
    if cc not in service.get_filter_options(company_id)["ccs"]:
        cc = None
    q = (request.args.get("q") or "").strip()[:100]
    page = max(1, _to_int(request.args.get("page")) or 1)
    return cc, q, page


@bp.route("/append-table")
@jwt_html_required
def append_table():
    """One page of the Append table (Data Sync tab); the page refetches it on every filter change."""
    company_id = session.get("company_id")
    if not company_id:
        return "", 400
    cc, q, page = _append_args(company_id)
    res = service.query_append(company_id, cc, q=q, limit=APPEND_PAGE_SIZE,
                               offset=(page - 1) * APPEND_PAGE_SIZE)
    pages = max(1, -(-res["total"] // APPEND_PAGE_SIZE))
    if page > pages:
        page = pages
        res = service.query_append(company_id, cc, q=q, limit=APPEND_PAGE_SIZE,
                                   offset=(page - 1) * APPEND_PAGE_SIZE)
    return render_template("management_report/_append_table.html",
                           rows=res["rows"], total=res["total"], page=page, pages=pages,
                           has_snapshot=service.get_active_upload_id(company_id) is not None)


@bp.route("/append/export")
@jwt_html_required
def append_export():
    """Everything that passes the Data Sync table's CC and search filters, as one xlsx."""
    company_id = session.get("company_id")
    if not company_id:
        return jsonify({"ok": False, "pesan": "Pilih perusahaan terlebih dahulu."}), 400
    cc, q, _ = _append_args(company_id)
    rows = service.query_append(company_id, cc, q=q)["rows"]
    if not rows:
        return jsonify({"ok": False, "pesan": "Tidak ada data Append untuk diexport."}), 404
    return _attachment(exports.build_append_workbook(rows), "Append.xlsx", _XLSX)


```
(`_attachment` and `_XLSX` are defined further down in the same module; they are looked up at call time, so the order is fine.)

(b) In `export_one`, replace
```python
    ho = ho_report.build_ho_report(company_id, real, f["yy"], f["mm"])
    data = exports.build_cc_workbook(report, f, ho)
```
with
```python
    ho = ho_report.build_ho_report(company_id, real, f["yy"], f["mm"])
    append_rows = service.query_append(company_id, real, f["yy"], f["mm"], f["coas"])["rows"]
    data = exports.build_cc_workbook(report, f, ho, append_rows)
```
(c) In `export_all`, replace
```python
    reports, ho_by_cc = [], {}
```
with
```python
    reports, ho_by_cc, append_by_cc = [], {}, {}
```
and replace
```python
        ho_by_cc[cc] = ho_report.build_ho_report(company_id, cc, f["yy"], f["mm"])
```
with
```python
        ho_by_cc[cc] = ho_report.build_ho_report(company_id, cc, f["yy"], f["mm"])
        append_by_cc[cc] = service.query_append(company_id, cc, f["yy"], f["mm"], f["coas"])["rows"]
```
and replace `    data = exports.build_zip(reports, f, ho_by_cc)` with `    data = exports.build_zip(reports, f, ho_by_cc, append_by_cc)`.

- [ ] **Step 4: Create `templates/management_report/_append_table.html`**

```html
{% macro v(x) %}{{ x if x is not none else '' }}{% endmacro %}
{% if not has_snapshot %}
<div class="mr-muted">Belum ada data. Sync dulu.</div>
{% else %}
<div class="mr-muted" style="margin:.25rem 0 .5rem">{{ total | mr_num(0) }} baris</div>
<div class="budget-table-container" style="max-height:60vh">
<table class="budget-table mr-append-table">
  <thead><tr>
    <th>COA</th><th>MM</th><th>YY</th><th>CC</th><th>Category</th><th>Activity</th><th>Description</th>
    <th>PTA</th><th>Custom</th><th>MM.1</th><th>ACT</th><th>BGT</th>
  </tr></thead>
  <tbody>
  {% for r in rows %}
    <tr>
      <td>{{ v(r.coa) }}</td><td>{{ v(r.mm) }}</td><td>{{ v(r.yy) }}</td><td>{{ v(r.cc) }}</td>
      <td>{{ v(r.category) }}</td><td>{{ v(r.activity) }}</td><td class="mr-wrap">{{ v(r.description) }}</td>
      <td class="num-right">{{ r.pta | mr_num(2) }}</td><td>{{ v(r.custom) }}</td><td>{{ v(r.mm1) }}</td>
      <td class="num-right">{{ r.act | mr_num(2) }}</td><td class="num-right">{{ r.bgt | mr_num(2) }}</td>
    </tr>
  {% else %}
    <tr><td colspan="12">Tidak ada baris untuk filter ini.</td></tr>
  {% endfor %}
  </tbody>
</table>
</div>
<div class="mr-pager">
  <button type="button" class="budget-btn" data-page="{{ page - 1 }}" {% if page <= 1 %}disabled{% endif %}>Sebelumnya</button>
  <span class="mr-muted">Halaman {{ page }} dari {{ pages }}</span>
  <button type="button" class="budget-btn" data-page="{{ page + 1 }}" {% if page >= pages %}disabled{% endif %}>Berikutnya</button>
</div>
{% endif %}
```

- [ ] **Step 5: Edit `templates/management_report/index.html`**

(a) CSS. Replace
```
.mr-muted { color:var(--sl-500); font-size:.8125rem; }

/* Report / HO Report tabs
```
with
```
.mr-muted { color:var(--sl-500); font-size:.8125rem; }

/* Data Append table (Data Sync tab) */
.budget-page.mr-append-scope { padding:0; background:transparent; }
#mr-append { margin-top:.25rem; transition:opacity .12s; }
#mr-append.mr-loading { opacity:.45; }
.mr-append-table { white-space:nowrap; font-size:.8rem; }
.mr-append-table td.mr-wrap { white-space:normal; min-width:360px; }
.mr-pager { display:flex; align-items:center; gap:.75rem; margin:.6rem 0 .2rem; }
.mr-pager .budget-btn[disabled] { opacity:.45; cursor:default; box-shadow:none; }

/* Report / HO Report tabs
```
(b) Markup. Replace
```
</div>
</div>

<div class="budget-page">
{% if not options.ccs %}
```
with
```
</div>

<div class="card" style="margin-bottom:1rem">
  <strong>Data Append</strong> <span class="mr-muted">(snapshot aktif)</span>
  {% if not options.ccs %}
  <div class="mr-muted" style="margin:.4rem 0">Belum ada data. Sync dulu.</div>
  {% else %}
  <div class="budget-page mr-append-scope">
    <div class="budget-toolbar" id="mr-append-toolbar">
      <div class="mr-field"><label for="mr-append-cc">CC</label>
        <select id="mr-append-cc">
          <option value="ALL">All Cost Center</option>
          {% for c in options.ccs %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
        </select></div>
      <div class="mr-field" style="flex:1"><label for="mr-append-q">Cari</label>
        <input type="search" id="mr-append-q" placeholder="COA, category, activity, description"></div>
      <div class="mr-actions">
        <a class="budget-btn" id="mr-append-export" href="/management-report/append/export">Export Append (Excel)</a>
      </div>
    </div>
    <div id="mr-append"></div>
  </div>
  {% endif %}
</div>
</div>

<div class="budget-page">
{% if not options.ccs %}
```
(c) JS. Replace
```
  if (window.ResizeObserver) new ResizeObserver(sizeWraps).observe(bar);   // the bar opens/closes with F/Esc
  syncCoaUi();
})();
</script>
```
with
```
  if (window.ResizeObserver) new ResizeObserver(sizeWraps).observe(bar);   // the bar opens/closes with F/Esc
  syncCoaUi();
})();

/* Data Append table (Data Sync tab): loaded on first view, then on every filter/page change. */
(function () {
  const box = document.getElementById('mr-append');
  if (!box) return;                                    // no data synced yet
  const cc = document.getElementById('mr-append-cc'), q = document.getElementById('mr-append-q'),
        exp = document.getElementById('mr-append-export');
  let page = 1, loaded = false, seq = 0, timer = null;

  function params(withPage) {
    const p = new URLSearchParams();
    if (cc.value !== 'ALL') p.set('cc', cc.value);
    if (q.value.trim()) p.set('q', q.value.trim());
    if (withPage) p.set('page', page);
    return p;
  }

  async function load() {
    const mine = ++seq;
    box.classList.add('mr-loading');
    try {
      const r = await fetch('/management-report/append-table?' + params(true), {credentials: 'same-origin'});
      if (r.redirected || !r.ok) { location.reload(); return; }   // session expired
      const html = await r.text();
      if (mine !== seq) return;                        // a newer request is already running
      box.innerHTML = html;
      loaded = true;
      const qs = params(false).toString();
      exp.href = '/management-report/append/export' + (qs ? '?' + qs : '');
    } catch (e) {
      const err = document.createElement('div');
      err.className = 'mr-muted';
      err.textContent = 'Gagal memuat data Append: ' + e;
      box.replaceChildren(err);
    } finally {
      if (mine === seq) box.classList.remove('mr-loading');
    }
  }

  function filterChanged() { page = 1; clearTimeout(timer); timer = setTimeout(load, 250); }
  cc.addEventListener('change', filterChanged);
  q.addEventListener('input', filterChanged);
  box.addEventListener('click', e => {
    const b = e.target.closest('button[data-page]');
    if (b && !b.disabled) { page = parseInt(b.dataset.page, 10) || 1; load(); }
  });
  const syncTab = document.querySelector('.tab-btn[data-tab="tab-sync"]');
  if (syncTab) syncTab.addEventListener('click', () => { if (!loaded) load(); });
})();
</script>
```

- [ ] **Step 6: Run the tests**

Run: `python -m pytest tests/test_mr_routes.py tests/test_mr_exports.py tests/test_mr_append.py tests/test_mr_meta.py tests/test_mr_ho_report.py tests/test_mr_ho_template.py tests/test_mr_service.py tests/test_mr_report.py tests/test_mr_parser.py tests/test_mr_sync.py tests/test_mr_reconciliation.py tests/test_mr_formatting.py tests/test_dashboard.py -q`
Expected: all pass.

---

### Task 4: Verification (controller)

- [ ] **Step 1: Real-data end-to-end (script)** On a throwaway database seeded from the real master workbook (`sync_rows` with `read_meta`), through the Flask test client: `/management-report/append-table` shows `8.388 baris` and `Halaman 1 dari 84`; `/append/export` has 8,388 data rows and sheet `Append`; `/export?cc=POOFFM` has the third sheet `Append` whose BGT sum equals the Grand Total BGT of sheet `Report`, also for `cc=ALL` and with `mm=3`; `/export-all` ZIP: every file has 3 sheets and the sum of all per-CC Append rows equals 8,388.

- [ ] **Step 2: Browser check** Throwaway instance (port 8090, temp database): open `?tab=sync`; the Data Append table loads, the pager moves between pages, the CC filter and the search refresh in place, the export link follows the filters; the Report tab export link still downloads a workbook with three sheets. Stop the instance and delete its database afterwards.

- [ ] **Step 3: Regression** Run the Step 6 command of Task 3 once more.

- [ ] **Step 4: Report to the user** with the test results, the real-data figures, the browser findings, and a reminder that the server must be restarted (templates are cached) and that nothing was committed.
