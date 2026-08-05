# Sponsorship MR (Management Report) Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new "MR" tab to the Sponsorship module (SMT company only) that displays sponsorship transactions in a fixed 17-column Management Report format and exports them to Excel, replacing the manual spreadsheet workflow.

**Architecture:** One new service function (`get_sponsorship_mr`) computes all 17 columns from `sponsorship_transaksi` rows, filtered only by year and sorted chronologically with a per-year running sequence for the "New Code" column. That function is the single source of truth consumed by both the on-screen table (server-rendered Jinja, like the Data/Outstanding tabs) and the Excel export (openpyxl, like the existing Report/Outstanding exports) — no duplicated logic between the two.

**Tech Stack:** Flask (server-rendered Jinja templates), SQLite via `database.get_conn()`, openpyxl for Excel export, pytest for tests.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-05-sponsorship-mr-tab-design.md` — all column mappings, decisions, and formulas below are copied verbatim from it.
- MR is filtered **only by Tahun** — no cat/pillar/description/status filters (spec decision #2).
- "New Code" sequence resets to 1 every time the year (CC0) changes (spec decision #3).
- Rows are sorted `tanggal_form_sponsor ASC`, tie-break `id ASC` (spec decision #4) — NOT the `DESC` order used by the Data tab.
- All 17 columns are **read-only** — no manual edit UI on the MR screen (spec decision #7).
- All values are computed in Python and written as **final values**, never live Excel formulas (spec decision #8), matching `export_report_excel`/`export_data_excel`/`export_outstanding_excel` in `modules/sponsorship/exports.py`.
- The export route MUST carry its own `@smt_company_required` guard, not just rely on the page's `wrong_company` flag — this is a named security requirement in the spec (citing the 2026-07-14 Bank Sahabat ETF finding).
- No pagination on the MR table (spec decision #9).
- Fixed-value columns (Account Management, COST CENTER, Source, COA HO, COST CENTER2, CC1, BC1, BC) live in `config.py` as named constants, not hardcoded in `service.py`/`exports.py`.

---

## File Structure

- **Modify `config.py`** — add 8 `SPONSORSHIP_MR_*` constants (Task 1).
- **Modify `modules/sponsorship/service.py`** — add `get_sponsorship_mr(company_id, tahun)` (Task 1).
- **Modify `modules/sponsorship/exports.py`** — add `export_mr_excel(company_id, tahun)` (Task 2).
- **Modify `modules/sponsorship/routes.py`** — add `_parse_mr_params()`, `mr_page()`, `export_mr_route()` (Task 3).
- **Create `templates/sponsorship/mr.html`** — filter bar + 17-column table + export button (Task 3).
- **Modify `templates/sponsorship/_toolbar.html`** — add "MR" tab link (Task 3).
- **Create `tests/test_sponsorship_mr_service.py`** (Task 1).
- **Create `tests/test_sponsorship_mr_export.py`** (Task 2).
- **Modify `tests/test_sponsorship_routes.py`** — append MR route tests (Task 3).

---

### Task 1: Service layer — `get_sponsorship_mr()`

**Files:**
- Modify: `config.py:58` (append after `SPONSORSHIP_PILLARS`)
- Modify: `modules/sponsorship/service.py` (append after `get_sponsorship_outstanding`, end of file — currently ends at line 625)
- Test: `tests/test_sponsorship_mr_service.py`

**Interfaces:**
- Produces: `get_sponsorship_mr(company_id: int, tahun: list) -> list[dict]`. Each dict has exactly these keys: `account_management` (int), `id_no` (str, always `""`), `date` (`datetime`), `date_display` (str, `"DD-Mon-YY"`), `allocation_memo` (str), `budget_activity` (str, always `""`), `cost_center` (str), `debit_credit` (float), `source` (str), `coa_ho` (int), `cost_center2` (str), `month` (int, 1-12), `cc0` (str, 2 chars), `cc1` (int), `bc1` (str), `new_code` (str), `memo` (str), `bc` (str). This is what Task 2 (`export_mr_excel`) and Task 3 (`mr.html` template) consume.

- [ ] **Step 1: Write the failing tests**

Create `C:\Financehub\app\tests\test_sponsorship_mr_service.py`:

```python
from datetime import datetime
from modules.sponsorship.service import seed_perusahaan, create_transaksi, get_sponsorship_mr

SMT = 1


def _seed():
    seed_perusahaan([("SMART", "AGRI", "AGRI"), ("IKPP", "APP", "APP")])


def _payload(**overrides):
    payload = {
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-20", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "perihal": "Bantuan Banjir",
        "amount_request": 25000000,
    }
    payload.update(overrides)
    return payload


def test_mr_maps_all_columns_for_single_row(app):
    _seed()
    create_transaksi(SMT, _payload())
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert len(rows) == 1
    r = rows[0]
    assert r["account_management"] == 70107800
    assert r["id_no"] == ""
    assert r["date"] == datetime(2026, 1, 20)
    assert r["date_display"] == "20-Jan-26"
    assert r["allocation_memo"] == "Sosial - Yayasan Test - Bantuan Banjir"
    assert r["budget_activity"] == ""
    assert r["cost_center"] == "POSPON"
    assert r["debit_credit"] == 25000000
    assert r["source"] == "Sponsor"
    assert r["coa_ho"] == 70107800
    assert r["cost_center2"] == "$POCCOM"
    assert r["month"] == 1
    assert r["cc0"] == "26"
    assert r["cc1"] == 5
    assert r["bc1"] == "-25-"
    assert r["new_code"] == "A26-5-25-1"
    assert r["memo"] == "- Act 2026 : Sosial - Yayasan Test - Bantuan Banjir Month : 1"
    assert r["bc"] == "Sponsorship - Non Building"


def test_mr_allocation_memo_skips_empty_perihal(app):
    _seed()
    create_transaksi(SMT, _payload(perihal=None))
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert rows[0]["allocation_memo"] == "Sosial - Yayasan Test"
    assert rows[0]["memo"] == "- Act 2026 : Sosial - Yayasan Test Month : 1"


def test_mr_new_code_increments_within_same_year(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-05", lembaga_perorangan="A"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-20", lembaga_perorangan="B"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-03-01", lembaga_perorangan="C"))
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert [r["new_code"] for r in rows] == ["A26-5-25-1", "A26-5-25-2", "A26-5-25-3"]


def test_mr_new_code_resets_per_year(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-05", lembaga_perorangan="A"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2025-06-01", lembaga_perorangan="B"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-02-01", lembaga_perorangan="C"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2025-07-01", lembaga_perorangan="D"))
    rows = get_sponsorship_mr(SMT, ["2025", "2026"])
    by_lembaga = {r["allocation_memo"].split(" - ")[1]: r["new_code"] for r in rows}
    assert by_lembaga["B"] == "A25-5-25-1"
    assert by_lembaga["D"] == "A25-5-25-2"
    assert by_lembaga["A"] == "A26-5-25-1"
    assert by_lembaga["C"] == "A26-5-25-2"


def test_mr_rows_sorted_by_date_ascending_then_id(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-03-01", lembaga_perorangan="Later"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-01", lembaga_perorangan="Earlier1"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-01-01", lembaga_perorangan="Earlier2"))
    rows = get_sponsorship_mr(SMT, ["2026"])
    order = [r["allocation_memo"].split(" - ")[1] for r in rows]
    assert order == ["Earlier1", "Earlier2", "Later"]


def test_mr_includes_all_rows_regardless_of_cat_or_description(app):
    _seed()
    create_transaksi(SMT, _payload(cat="CSR Gedung", description="Akademisi", lembaga_perorangan="X"))
    create_transaksi(SMT, _payload(cat="Sponsorship", description="Media", lembaga_perorangan="Y"))
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert len(rows) == 2


def test_mr_respects_company_scope(app):
    _seed()
    create_transaksi(SMT, _payload(lembaga_perorangan="SMT Row"))
    create_transaksi(2, _payload(lembaga_perorangan="Other Company Row"))
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert len(rows) == 1
    assert rows[0]["allocation_memo"].split(" - ")[1] == "SMT Row"


def test_mr_filters_by_tahun(app):
    _seed()
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2025-06-01", lembaga_perorangan="Old"))
    create_transaksi(SMT, _payload(tanggal_form_sponsor="2026-06-01", lembaga_perorangan="New"))
    rows = get_sponsorship_mr(SMT, ["2026"])
    assert len(rows) == 1
    assert rows[0]["allocation_memo"].split(" - ")[1] == "New"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_mr_service.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_sponsorship_mr'`

- [ ] **Step 3: Add config constants**

In `C:\Financehub\app\config.py`, after line 58 (`SPONSORSHIP_PILLARS = ["APP", "AGRI", "ENERGY & FINANCE", "PROPERTY"]`), add:

```python

# Sponsorship MR (Management Report) — fixed defaults. See
# docs/superpowers/specs/2026-08-05-sponsorship-mr-tab-design.md
SPONSORSHIP_MR_ACCOUNT_MANAGEMENT = 70107800
SPONSORSHIP_MR_COST_CENTER        = "POSPON"
SPONSORSHIP_MR_SOURCE             = "Sponsor"
SPONSORSHIP_MR_COA_HO             = 70107800
SPONSORSHIP_MR_COST_CENTER2       = "$POCCOM"
SPONSORSHIP_MR_CC1                = 5
SPONSORSHIP_MR_BC1                = "-25-"
SPONSORSHIP_MR_BC                 = "Sponsorship - Non Building"
```

- [ ] **Step 4: Implement `get_sponsorship_mr`**

In `C:\Financehub\app\modules\sponsorship\service.py`, append at the end of the file (after `get_sponsorship_outstanding`, currently ending at line 625):

```python


def get_sponsorship_mr(company_id: int, tahun: list) -> list:
    """Rekap sponsorship jadi format MR (Management Report) — 17 kolom
    standar untuk upload ke sistem GL, satu baris per transaksi. Difilter
    HANYA oleh tahun (tidak ada filter cat/pillar/description/status —
    lihat spec §2/§9). Nomor urut 'New Code' reset ke 1 tiap ganti tahun
    (CC0) — lihat spec §3. Urutan baris: tanggal_form_sponsor ASC, lalu
    id ASC (spec §4)."""
    filters = {"tahun": tahun}
    rows = list_transaksi(company_id, filters)
    rows.sort(key=lambda r: (r["tanggal_form_sponsor"] or "", r["id"]))

    seq_by_year = {}
    mr_rows = []
    for r in rows:
        date_str = r["tanggal_form_sponsor"]
        year_full = date_str[:4]
        cc0 = date_str[2:4]
        month = int(date_str[5:7])
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            date_display = date_obj.strftime("%d-%b-%y")
        except (ValueError, TypeError):
            date_obj = None
            date_display = date_str or ""

        parts = [p for p in (r["description"], r["lembaga_perorangan"], r["perihal"]) if p]
        allocation_memo = " - ".join(parts)

        seq_by_year[cc0] = seq_by_year.get(cc0, 0) + 1
        seq = seq_by_year[cc0]
        new_code = f"A{cc0}-{config.SPONSORSHIP_MR_CC1}{config.SPONSORSHIP_MR_BC1}{seq}"

        mr_rows.append({
            "account_management": config.SPONSORSHIP_MR_ACCOUNT_MANAGEMENT,
            "id_no": "",
            "date": date_obj,
            "date_display": date_display,
            "allocation_memo": allocation_memo,
            "budget_activity": "",
            "cost_center": config.SPONSORSHIP_MR_COST_CENTER,
            "debit_credit": r["amount_request"],
            "source": config.SPONSORSHIP_MR_SOURCE,
            "coa_ho": config.SPONSORSHIP_MR_COA_HO,
            "cost_center2": config.SPONSORSHIP_MR_COST_CENTER2,
            "month": month,
            "cc0": cc0,
            "cc1": config.SPONSORSHIP_MR_CC1,
            "bc1": config.SPONSORSHIP_MR_BC1,
            "new_code": new_code,
            "memo": f"- Act {year_full} : {allocation_memo} Month : {month}",
            "bc": config.SPONSORSHIP_MR_BC,
        })
    return mr_rows
```

`datetime` is already imported at the top of `service.py` (`from datetime import datetime`, line 2) — no new import needed.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_mr_service.py -v`
Expected: PASS (8 tests)

- [ ] **Step 6: Commit**

```bash
cd C:\Financehub
git add app/config.py app/modules/sponsorship/service.py app/tests/test_sponsorship_mr_service.py
git commit -m "feat: add get_sponsorship_mr service function for Sponsorship MR tab

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Excel export — `export_mr_excel()`

**Files:**
- Modify: `modules/sponsorship/exports.py` (append at end of file, currently ending at line 281)
- Test: `tests/test_sponsorship_mr_export.py`

**Interfaces:**
- Consumes: `get_sponsorship_mr(company_id, tahun) -> list[dict]` from Task 1 (exact keys listed in Task 1's Interfaces block).
- Produces: `export_mr_excel(company_id: int, tahun: list) -> bytes` — an `.xlsx` file, one row per dict from `get_sponsorship_mr`, columns in the exact order: Account Management, ID#, Date, Allocation Memo, Budget Activity, COST CENTER, DEBIT - CREDIT, Source, COA HO, COST CENTER2, Month, CC0, CC1, BC1, New Code, Memo, BC. This is what Task 3's `export_mr_route()` calls.

- [ ] **Step 1: Write the failing tests**

Create `C:\Financehub\app\tests\test_sponsorship_mr_export.py`:

```python
import io
import openpyxl
from modules.sponsorship.service import seed_perusahaan, create_transaksi
from modules.sponsorship.exports import export_mr_excel

SMT = 1


def _seed():
    seed_perusahaan([("SMART", "AGRI", "AGRI")])


def _payload(**overrides):
    payload = {
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-20", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "perihal": "Bantuan Banjir",
        "amount_request": 25000000,
    }
    payload.update(overrides)
    return payload


def test_export_mr_excel_has_expected_headers(app):
    _seed()
    xls_bytes = export_mr_excel(SMT, ["2026"])
    wb = openpyxl.load_workbook(io.BytesIO(xls_bytes))
    ws = wb.active
    headers = [c.value for c in ws[1]]
    assert headers == [
        "Account Management", "ID#", "Date", "Allocation Memo", "Budget Activity",
        "COST CENTER", "DEBIT - CREDIT", "Source", "COA HO", "COST CENTER2",
        "Month", "CC0", "CC1", "BC1", "New Code", "Memo", "BC",
    ]


def test_export_mr_excel_matches_worked_example_constants(app):
    _seed()
    create_transaksi(SMT, _payload(
        perihal="Partisipasi Pemasangan Lampion dan Lilin Tahun Baru Imlek 2026",
        tanggal_form_sponsor="2026-01-20", amount_request=25000000,
    ))
    create_transaksi(SMT, _payload(
        perihal="Prasasti Membership",
        tanggal_form_sponsor="2026-01-20", amount_request=500000000,
    ))
    xls_bytes = export_mr_excel(SMT, ["2026"])
    wb = openpyxl.load_workbook(io.BytesIO(xls_bytes))
    ws = wb.active
    row1 = [c.value for c in ws[2]]
    row2 = [c.value for c in ws[3]]
    assert row1[0] == 70107800          # Account Management
    assert row1[5] == "POSPON"          # COST CENTER
    assert row1[6] == 25000000          # DEBIT - CREDIT
    assert row1[7] == "Sponsor"         # Source
    assert row1[8] == 70107800          # COA HO
    assert row1[9] == "$POCCOM"         # COST CENTER2
    assert row1[10] == 1                # Month
    assert row1[11] == "26"             # CC0
    assert row1[12] == 5                # CC1
    assert row1[13] == "-25-"           # BC1
    assert row1[14] == "A26-5-25-1"     # New Code
    assert row1[16] == "Sponsorship - Non Building"  # BC
    assert row2[6] == 500000000         # DEBIT - CREDIT
    assert row2[14] == "A26-5-25-2"     # New Code increments


def test_export_mr_excel_empty_data_still_generates_file(app):
    _seed()
    xls_bytes = export_mr_excel(SMT, ["2026"])
    wb = openpyxl.load_workbook(io.BytesIO(xls_bytes))
    ws = wb.active
    assert ws["A1"].value == "Account Management"
    assert ws.max_row == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_mr_export.py -v`
Expected: FAIL with `ImportError: cannot import name 'export_mr_excel'`

- [ ] **Step 3: Implement `export_mr_excel`**

In `C:\Financehub\app\modules\sponsorship\exports.py`, append at the end of the file (after `export_outstanding_excel`, currently ending at line 281):

```python


_MR_HEADERS = [
    "Account Management", "ID#", "Date", "Allocation Memo", "Budget Activity",
    "COST CENTER", "DEBIT - CREDIT", "Source", "COA HO", "COST CENTER2",
    "Month", "CC0", "CC1", "BC1", "New Code", "Memo", "BC",
]
_MR_ROW_KEYS = [
    "account_management", "id_no", "date", "allocation_memo", "budget_activity",
    "cost_center", "debit_credit", "source", "coa_ho", "cost_center2",
    "month", "cc0", "cc1", "bc1", "new_code", "memo", "bc",
]
_MR_RED_FILL = PatternFill("solid", fgColor="C00000")
_MR_DATE_FMT = "dd-mmm-yy"
_MR_NUM_FMT = '#,##0;-#,##0;"-"'
_MR_COL_WIDTHS = [16, 8, 12, 55, 14, 12, 16, 10, 12, 14, 8, 6, 6, 8, 14, 60, 22]


def export_mr_excel(company_id: int, tahun: list) -> bytes:
    from modules.sponsorship.service import get_sponsorship_mr
    rows = get_sponsorship_mr(company_id, tahun)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "MR"

    ws.append(_MR_HEADERS)
    for col in range(1, len(_MR_HEADERS) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = ARIAL_11_WHITE_BOLD
        cell.alignment = ALIGN_CENTER
        cell.fill = _MR_RED_FILL if 9 <= col <= 14 else DARK_BLUE_FILL

    for r in rows:
        ws.append([r[key] for key in _MR_ROW_KEYS])
        row_idx = ws.max_row
        for col, key in enumerate(_MR_ROW_KEYS, start=1):
            cell = ws.cell(row=row_idx, column=col)
            cell.font = ARIAL_11
            if key == "date":
                cell.number_format = _MR_DATE_FMT
            elif key in ("account_management", "coa_ho", "debit_credit"):
                cell.number_format = _MR_NUM_FMT
                cell.alignment = ALIGN_RIGHT

    for i, w in enumerate(_MR_COL_WIDTHS, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

This reuses `ARIAL_11`, `ARIAL_11_WHITE_BOLD`, `DARK_BLUE_FILL`, `ALIGN_CENTER`, `ALIGN_RIGHT`, `io`, and `openpyxl`, all already defined/imported at the top of `exports.py` (lines 1-20) — no new imports needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_mr_export.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/modules/sponsorship/exports.py app/tests/test_sponsorship_mr_export.py
git commit -m "feat: add export_mr_excel for Sponsorship MR tab

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Routes, template, and toolbar link

**Files:**
- Modify: `modules/sponsorship/routes.py:8-13` (imports), `:96-97` (add `_parse_mr_params` after `_parse_report_params`), `:254-256` (add `mr_page`/`export_mr_route` after `report_page`)
- Create: `templates/sponsorship/mr.html`
- Modify: `templates/sponsorship/_toolbar.html`
- Modify: `tests/test_sponsorship_routes.py` (append)

**Interfaces:**
- Consumes: `get_sponsorship_mr(company_id, tahun)` (Task 1), `export_mr_excel(company_id, tahun)` (Task 2).
- Produces: `GET /sponsorship/mr` (page), `GET /sponsorship/mr/export` (xlsx download) — both registered on Blueprint `sponsorship.mr_page` / `sponsorship.export_mr_route`.

- [ ] **Step 1: Write the failing tests**

Append to `C:\Financehub\app\tests\test_sponsorship_routes.py` (uses the file's existing `login`, `_select_smt`, `_select_etf`, `_seed` helpers — no new imports needed):

```python


def test_mr_page_renders_with_data(client):
    login(client)
    _select_smt(client)
    _seed()
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-20", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "perihal": "Bantuan Banjir",
        "amount_request": 1000,
    })
    resp = client.get("/sponsorship/mr?tahun=2026")
    assert resp.status_code == 200
    assert b"Yayasan Test" in resp.data
    assert b"A26-5-25-1" in resp.data


def test_mr_page_shows_wrong_company_notice_for_etf(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/mr")
    assert resp.status_code == 200
    assert b"Ganti Company" in resp.data


def test_mr_export_downloads_xlsx(client):
    login(client)
    _select_smt(client)
    _seed()
    client.post("/sponsorship/input/create", json={
        "cat": "Sponsorship", "description": "Sosial",
        "tanggal_form_sponsor": "2026-01-20", "cat1": "SMART",
        "lembaga_perorangan": "Yayasan Test", "amount_request": 1000,
    })
    resp = client.get("/sponsorship/mr/export?tahun=2026")
    assert resp.status_code == 200
    assert resp.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_mr_export_rejects_non_smt(client):
    login(client)
    _select_etf(client)
    resp = client.get("/sponsorship/mr/export")
    assert resp.status_code == 403


def test_mr_tab_in_toolbar(client):
    login(client)
    _select_smt(client)
    resp = client.get("/sponsorship/report")
    assert resp.status_code == 200
    assert b'href="/sponsorship/mr"' in resp.data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_routes.py -v -k mr`
Expected: FAIL with 404s / `werkzeug.routing.exceptions.BuildError` (routes don't exist yet)

- [ ] **Step 3: Update imports in `routes.py`**

In `C:\Financehub\app\modules\sponsorship\routes.py`, replace lines 8-13:

```python
from modules.sponsorship.service import (
    list_perusahaan, get_lembaga_suggestions, create_transaksi, get_transaksi,
    update_transaksi, list_transaksi, count_transaksi, get_available_years,
    get_dashboard_data, get_sponsorship_report,
)
from modules.sponsorship.exports import export_report_excel
```

with:

```python
from modules.sponsorship.service import (
    list_perusahaan, get_lembaga_suggestions, create_transaksi, get_transaksi,
    update_transaksi, list_transaksi, count_transaksi, get_available_years,
    get_dashboard_data, get_sponsorship_report, get_sponsorship_mr,
)
from modules.sponsorship.exports import export_report_excel, export_mr_excel
```

- [ ] **Step 4: Add `_parse_mr_params()`**

In `C:\Financehub\app\modules\sponsorship\routes.py`, after `_parse_report_params()` (the function ending at line 96 with `return tahun, cat4`), add:

```python


def _parse_mr_params():
    tahun_vals = request.args.getlist("tahun")
    tahun = [y for y in tahun_vals if y.strip()]
    if not tahun:
        years = get_available_years(_cid())
        tahun = [years[0]] if years else [str(datetime.now().year)]
    return tahun
```

- [ ] **Step 5: Add `mr_page()` and `export_mr_route()`**

In `C:\Financehub\app\modules\sponsorship\routes.py`, after `report_page()` (the function ending at line 254 with `**_ctx())`), add:

```python


@bp.route("/mr")
@jwt_html_required
def mr_page():
    tahun = _parse_mr_params() if not _wrong_company() else []
    years = get_available_years(_cid()) if not _wrong_company() else []
    rows = get_sponsorship_mr(_cid(), tahun) if not _wrong_company() else []
    return render_template(
        "sponsorship/mr.html", active_page="sponsorship", use_unified_header=True,
        wrong_company=_wrong_company(),
        rows=rows, years=years, tahun=tahun,
        **_ctx()
    )


@bp.route("/mr/export")
@jwt_html_required
@smt_company_required
def export_mr_route():
    tahun = _parse_mr_params()
    xls_bytes = export_mr_excel(_cid(), tahun)
    filename = f"Sponsorship_MR_{'-'.join(tahun)}.xlsx"
    return send_file(
        io.BytesIO(xls_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=filename,
        as_attachment=True,
    )
```

`io` and `send_file` are already imported at the top of `routes.py` (lines 4-5) — no new imports needed.

- [ ] **Step 6: Create the template**

Create `C:\Financehub\app\templates\sponsorship\mr.html`:

```html
{% extends "base.html" %}
{% set full_bleed = true %}
{% block title %}Sponsorship MR
{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/sponsorship.css') }}">
<style>
.mr-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
  background: var(--bg-card);
  white-space: nowrap;
}
.mr-table th, .mr-table td {
  border: 1px solid var(--border-color);
  padding: 0.4rem 0.55rem;
}
.mr-table th {
  color: #fff;
  text-align: center;
  position: sticky;
  top: 0;
  z-index: 10;
}
.mr-table th.mr-navy { background: #1e3a5f; }
.mr-table th.mr-red { background: #c00000; }
.mr-table td.num-right { text-align: right; }
.mr-table td.mr-memo { white-space: normal; min-width: 320px; }
</style>
{% endblock %}
{% block module_tabs %}
{% set active_tab = "mr" %}
{% include "sponsorship/_toolbar.html" with context %}
{% endblock %}
{% block content %}
<div class="budget-page">
  {% if wrong_company %}
    {% include "sponsorship/_notice.html" %}
  {% else %}
  <form class="budget-toolbar filter-bar collapsible" method="get" id="sp-mr-filter-form">
    <div class="budget-dropdown-check">
      <button type="button" class="budget-dropdown-btn" onclick="this.nextElementSibling.classList.toggle('show')">
        Tahun <span style="font-size: 0.7em;">▼</span>
      </button>
      <div class="budget-dropdown-content">
        {% for y in years %}
        <label><input type="checkbox" name="tahun" value="{{ y }}" {% if y in tahun %}checked{% endif %}> {{ y }}</label>
        {% endfor %}
      </div>
    </div>
    <button type="submit" class="budget-btn">Terapkan Filter</button>
    <button type="button" class="budget-btn" style="background-color:#10b981;margin-left:auto" onclick="exportMrExcel()">Export to Excel</button>
  </form>

  <div class="budget-table-container" id="sp-table-wrap">
    <table class="mr-table">
      <thead>
        <tr>
          <th class="mr-navy">Account<br>Management</th>
          <th class="mr-navy">ID#</th>
          <th class="mr-navy">Date</th>
          <th class="mr-navy">Allocation Memo</th>
          <th class="mr-navy">Budget Activity</th>
          <th class="mr-navy">COST CENTER</th>
          <th class="mr-navy">DEBIT - CREDIT</th>
          <th class="mr-navy">Source</th>
          <th class="mr-red">COA HO</th>
          <th class="mr-red">COST CENTER2</th>
          <th class="mr-red">Month</th>
          <th class="mr-red">CC0</th>
          <th class="mr-red">CC1</th>
          <th class="mr-red">BC1</th>
          <th class="mr-navy">New Code</th>
          <th class="mr-navy">Memo</th>
          <th class="mr-navy">BC</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td class="num-right">{{ r.account_management | rupiah(false) }}</td>
          <td>{{ r.id_no }}</td>
          <td>{{ r.date_display }}</td>
          <td>{{ r.allocation_memo }}</td>
          <td>{{ r.budget_activity }}</td>
          <td>{{ r.cost_center }}</td>
          <td class="num-right">{{ r.debit_credit | rupiah(false) }}</td>
          <td>{{ r.source }}</td>
          <td class="num-right">{{ r.coa_ho | rupiah(false) }}</td>
          <td>{{ r.cost_center2 }}</td>
          <td>{{ r.month }}</td>
          <td>{{ r.cc0 }}</td>
          <td>{{ r.cc1 }}</td>
          <td>{{ r.bc1 }}</td>
          <td>{{ r.new_code }}</td>
          <td class="mr-memo">{{ r.memo }}</td>
          <td>{{ r.bc }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}
</div>
{% endblock %}

<script>
function exportMrExcel() {
  const form = document.getElementById("sp-mr-filter-form");
  const params = new URLSearchParams(new FormData(form));
  window.location.href = "/sponsorship/mr/export?" + params.toString();
}
</script>
<script>
(function() {
  function sizeWrap() {
    const wrap = document.getElementById('sp-table-wrap');
    if (!wrap) return;
    requestAnimationFrame(() => {
      wrap.style.height = (window.innerHeight - wrap.getBoundingClientRect().top) + 'px';
    });
  }
  window.addEventListener('load', sizeWrap);
  window.addEventListener('resize', sizeWrap);
  document.addEventListener('DOMContentLoaded', sizeWrap);
  document.addEventListener('DOMContentLoaded', () => {
    const filterForm = document.getElementById('sp-mr-filter-form');
    if (filterForm && window.ResizeObserver) new ResizeObserver(sizeWrap).observe(filterForm);
  });
})();
</script>
```

- [ ] **Step 7: Add the toolbar link**

In `C:\Financehub\app\templates\sponsorship\_toolbar.html`, replace:

```html
<div class="tabs" style="margin-bottom:0">
  <a class="tab-btn{{ ' active' if active_tab == 'dashboard' else '' }}" href="{{ url_for('sponsorship.index') }}">Dashboard</a>
  <a class="tab-btn{{ ' active' if active_tab == 'input' else '' }}" href="{{ url_for('sponsorship.input_page') }}">Input</a>
  <a class="tab-btn{{ ' active' if active_tab == 'data' else '' }}" href="{{ url_for('sponsorship.data_page') }}">Data</a>
  <a class="tab-btn{{ ' active' if active_tab == 'outstanding' else '' }}" href="{{ url_for('sponsorship.outstanding_page') }}">Outstanding</a>
  <a class="tab-btn{{ ' active' if active_tab == 'report' else '' }}" href="{{ url_for('sponsorship.report_page') }}">Report</a>
</div>
```

with:

```html
<div class="tabs" style="margin-bottom:0">
  <a class="tab-btn{{ ' active' if active_tab == 'dashboard' else '' }}" href="{{ url_for('sponsorship.index') }}">Dashboard</a>
  <a class="tab-btn{{ ' active' if active_tab == 'input' else '' }}" href="{{ url_for('sponsorship.input_page') }}">Input</a>
  <a class="tab-btn{{ ' active' if active_tab == 'data' else '' }}" href="{{ url_for('sponsorship.data_page') }}">Data</a>
  <a class="tab-btn{{ ' active' if active_tab == 'outstanding' else '' }}" href="{{ url_for('sponsorship.outstanding_page') }}">Outstanding</a>
  <a class="tab-btn{{ ' active' if active_tab == 'report' else '' }}" href="{{ url_for('sponsorship.report_page') }}">Report</a>
  <a class="tab-btn{{ ' active' if active_tab == 'mr' else '' }}" href="{{ url_for('sponsorship.mr_page') }}">MR</a>
</div>
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_routes.py -v -k mr`
Expected: PASS (5 tests)

- [ ] **Step 9: Run the full Sponsorship test suite for regressions**

Run: `cd C:\Financehub\app && python -m pytest tests/test_sponsorship_routes.py tests/test_sponsorship_service.py tests/test_sponsorship_mr_service.py tests/test_sponsorship_mr_export.py tests/test_sponsorship_report_service.py tests/test_sponsorship_report_export.py -v`
Expected: PASS (all tests, no regressions in existing Sponsorship tests)

- [ ] **Step 10: Commit**

```bash
cd C:\Financehub
git add app/modules/sponsorship/routes.py app/templates/sponsorship/mr.html app/templates/sponsorship/_toolbar.html app/tests/test_sponsorship_routes.py
git commit -m "feat: add MR tab page, export route, and toolbar link

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Decision #1 (table + export) → Task 3 template + export route. ✓
- Decision #2 (Tahun-only filter) → Task 1 `get_sponsorship_mr` filters only on `tahun`; Task 3 template has no cat/pillar/description/status filter UI. ✓
- Decision #3 (reset per year) → Task 1 `seq_by_year` dict, tested in `test_mr_new_code_resets_per_year`. ✓
- Decision #4 (sort order) → Task 1 `rows.sort(...)`, tested in `test_mr_rows_sorted_by_date_ascending_then_id`. ✓
- Decision #5 (Month plain 1-12) → Task 1 `int(date_str[5:7])`, tested. ✓
- Decision #6 (Allocation Memo concat) → Task 1 `parts`/`allocation_memo`, tested in `test_mr_allocation_memo_skips_empty_perihal`. ✓
- Decision #7 (read-only) → Task 3 template has no input fields, only `{{ }}` output. ✓
- Decision #8 (final values, not formulas) → Task 2 `export_mr_excel` writes computed dict values directly. ✓
- Decision #9 (no pagination) → Task 3 `mr_page()` has no `page`/`page_size` params. ✓
- Column Mapping table (all 17 columns) → Task 1 `get_sponsorship_mr` return dict + Task 1's `test_mr_maps_all_columns_for_single_row` asserts every key. ✓
- Worked example (New Code sequence, Debit-Credit values) → `test_export_mr_excel_matches_worked_example_constants` in Task 2. ✓
- Architecture (shared service function, no duplicated logic) → Task 2 and Task 3 both call `get_sponsorship_mr`, never recompute columns themselves. ✓
- Routes/Template/Toolbar/Config sections → Task 3 (routes+template+toolbar), Task 1 (config). ✓
- Error Handling (empty tahun default, wrong company, null fields) → `_parse_mr_params()` defaults to latest year; `wrong_company` guard in Task 3; `allocation_memo` skip-empty handles nulls in Task 1. ✓
- Testing Plan (3 test files) → Task 1, Task 2, Task 3 each create/extend exactly the files named in the spec. ✓
- Out of Scope items are correctly not implemented (no edit UI, no extra filters, no Excel re-import). ✓

**Placeholder scan:** No TBD/TODO markers; every step has complete code and exact commands.

**Type consistency:** `get_sponsorship_mr` (Task 1) return keys match `_MR_ROW_KEYS` (Task 2) and the `{{ r.* }}` references in `mr.html` (Task 3) exactly — `account_management`, `id_no`, `date`, `date_display`, `allocation_memo`, `budget_activity`, `cost_center`, `debit_credit`, `source`, `coa_ho`, `cost_center2`, `month`, `cc0`, `cc1`, `bc1`, `new_code`, `memo`, `bc`. Route function names (`mr_page`, `export_mr_route`) match `url_for('sponsorship.mr_page')` in the toolbar and `test_mr_tab_in_toolbar`'s literal `href="/sponsorship/mr"` check.

---

## Note: pre-existing bug found during research (out of scope)

While reading `exports.py` for this plan, `export_outstanding_excel()` (lines 240-281, pre-existing code, not touched by this plan) references `_SECTION_FONT`, `_SECTION_FILL`, `_GRANDTOTAL_FONT`, `_GRANDTOTAL_FILL` — none of these are defined anywhere in the file. Any Outstanding export with at least one section will raise `NameError`. This is unrelated to the MR tab and is not fixed by this plan.
