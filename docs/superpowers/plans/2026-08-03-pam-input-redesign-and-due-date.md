# PAM Input Redesign & Due Date Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the Payment Approval Memo due-date calculation so one formula (`pam_date + 8 workdays`, skipping weekends and holidays) is used everywhere — stored at creation, shown at print, and previewed live in the Input form for every pillar — then apply the already-approved color-coded `.form-section` visual treatment to the Input form without changing its field layout.

**Architecture:** `_workday()`/`_HOLIDAYS_2026` move from `exports.py` into `service.py` (the lower-level module `exports.py` already depends on), becoming the single implementation every other piece calls: the 6 PAM-creation insert functions, a new `GET /payment-memo/api/due-date` endpoint, and (indirectly, via that endpoint) the Input form's JS. A one-off migration script recomputes `due_date` for every existing `pam_records` row.

**Tech Stack:** Flask/Jinja2, vanilla JS, SQLite, pytest.

## Global Constraints

- `_workday(start, n=8)` returns a `datetime` object (unchanged contract — 4 existing call sites in `exports.py` rely on this for Excel date-typed cells). Every new call site that stores the result into `pam_records.due_date` (a `"YYYY-MM-DD"` string column) must call `.strftime("%Y-%m-%d")` on it first — storing the bare `datetime` object would let sqlite3 stringify it as `"YYYY-MM-DD 00:00:00"`, breaking any code doing an exact-format `strptime(due_date, "%Y-%m-%d")` (e.g. `service.py:1987`).
- The Due Date field in the Input form is read-only, auto-calculated — no manual override (confirmed decision).
- The 3 visual sections (Identitas PAM / Metadata Auto / Detail Transaksi) reuse the existing `--accent`/`--violet`/`--tangerine` tokens and `.form-section`/`.tint-*` classes already shipped for the ETF PA Input redesign — no new CSS tokens.
- Existing field order/layout in the Input form is unchanged — only section framing and the one new field are added.
- `_add_one_month` is left in place, unused, per the design's explicit "not deleted" decision.

---

### Task 1: Move `_workday`/`_HOLIDAYS_2026` into `service.py`

**Files:**
- Modify: `app/modules/payment_memo/service.py:5` (import) and after `:246` (add function/constant)
- Modify: `app/modules/payment_memo/exports.py:4` (import), `:18-21` (import), `:23-49` (remove)
- Test: `app/tests/test_pam_service.py`

**Interfaces:**
- Produces: `modules.payment_memo.service._workday(start, n: int = 8) -> datetime` and `modules.payment_memo.service._HOLIDAYS_2026: set[date]` — consumed by Task 2 (due-date call sites) and Task 3 (API endpoint).

This task is a pure relocation — no behavior changes anywhere. `exports.py`'s 4 existing `_workday(...)` call sites keep working identically, just importing from a new place.

- [ ] **Step 1: Write the failing test**

Add to `app/tests/test_pam_service.py` (near the top, after the existing imports):

```python
from modules.payment_memo.service import _workday
```

Append this test function:

```python
def test_workday_skips_weekend_and_2026_holiday():
    # 2026-05-31 is a Sunday; 2026-06-01 is a holiday (Hari Lahir Pancasila
    # observed) — both must be skipped when counting 8 workdays forward.
    result = _workday("2026-05-31", 8)
    assert result.strftime("%Y-%m-%d") == "2026-06-11"


def test_workday_plain_weekday_span_no_holiday():
    # 2026-07-06 is a Monday with no holiday in the next 8 workdays.
    result = _workday("2026-07-06", 8)
    assert result.strftime("%Y-%m-%d") == "2026-07-16"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_service.py -v -k test_workday`
Expected: FAIL with `ImportError: cannot import name '_workday' from 'modules.payment_memo.service'`

- [ ] **Step 3: Move the code**

In `app/modules/payment_memo/service.py`, replace line 5:

```python
from datetime import datetime
```

with:

```python
from datetime import datetime, date, timedelta
```

In the same file, after `_add_one_month` (currently ending at line 246, right before `_PILLAR_LINES_TABLE = {`), insert:

```python
_HOLIDAYS_2026 = {
    date(2026, 1,  1), date(2026, 1, 16), date(2026, 2, 17),
    date(2026, 3, 19), date(2026, 3, 21), date(2026, 3, 22),
    date(2026, 4,  3), date(2026, 4,  5),
    date(2026, 5,  1), date(2026, 5, 14), date(2026, 5, 27), date(2026, 5, 31),
    date(2026, 6,  1), date(2026, 6, 16),
    date(2026, 8, 17), date(2026, 8, 25),
    date(2026, 12, 25),
}


def _workday(start, n: int = 8):
    """WORKDAY(start, n) — skip weekends and _HOLIDAYS_2026."""
    if isinstance(start, datetime):
        d = start.date()
    elif isinstance(start, date):
        d = start
    else:
        try:
            d = datetime.strptime(str(start)[:10], "%Y-%m-%d").date()
        except Exception:
            return start
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in _HOLIDAYS_2026:
            n -= 1
    return datetime(d.year, d.month, d.day)
```

In `app/modules/payment_memo/exports.py`, replace line 4:

```python
from datetime import datetime, date, timedelta
```

with:

```python
from datetime import datetime
```

Replace lines 18-21:

```python
from modules.payment_memo.service import (
    get_pam_detail, get_pam_payments, get_pam_payments_detail, 
    get_pam_transaction_lines
)
```

with:

```python
from modules.payment_memo.service import (
    get_pam_detail, get_pam_payments, get_pam_payments_detail, 
    get_pam_transaction_lines, _workday
)
```

Remove lines 23-49 (the `_HOLIDAYS_2026` set and `_workday` function definition — now superseded by the import above):

```python
_HOLIDAYS_2026 = {
    date(2026, 1,  1), date(2026, 1, 16), date(2026, 2, 17),
    date(2026, 3, 19), date(2026, 3, 21), date(2026, 3, 22),
    date(2026, 4,  3), date(2026, 4,  5),
    date(2026, 5,  1), date(2026, 5, 14), date(2026, 5, 27), date(2026, 5, 31),
    date(2026, 6,  1), date(2026, 6, 16),
    date(2026, 8, 17), date(2026, 8, 25),
    date(2026, 12, 25),
}


def _workday(start, n: int = 8):
    """WORKDAY(start, n) — skip weekends and HOLIDAYS_2026."""
    if isinstance(start, datetime):
        d = start.date()
    elif isinstance(start, date):
        d = start
    else:
        try:
            d = datetime.strptime(str(start)[:10], "%Y-%m-%d").date()
        except Exception:
            return start
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in _HOLIDAYS_2026:
            n -= 1
    return datetime(d.year, d.month, d.day)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_service.py -v -k test_workday`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the existing PAM export tests to confirm no regression**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_exports.py -v`
Expected: PASS — same result as before this change, since `_workday`'s behavior and every `exports.py` call site are unchanged.

- [ ] **Step 6: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/service.py app/modules/payment_memo/exports.py app/tests/test_pam_service.py
git commit -m "refactor: move _workday/_HOLIDAYS_2026 from exports.py into service.py"
```

---

### Task 2: Fix all 6 due-date call sites

**Files:**
- Modify: `app/modules/payment_memo/service.py:627, 671, 751, 844, 925, 2441`
- Test: `app/tests/test_pam_service.py`

**Interfaces:**
- Consumes: `_workday` (Task 1)

- [ ] **Step 1: Update the existing test's expected value**

In `app/tests/test_pam_service.py`, `test_create_pam_record_inserts_row` currently asserts (line 80):

```python
    assert row["due_date"]        == "2026-06-30"
```

Replace with:

```python
    assert row["due_date"]        == "2026-06-11"
```

(`create_pam_record` is called with `"pam_date": "2026-05-31"` — verified via `_workday("2026-05-31", 8)` = 2026-06-11: 2026-06-01 is a holiday and gets skipped along with the weekend, so the 8th workday lands on 2026-06-11, not 2026-06-30 from the old `+1 month` formula.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_service.py -v -k test_create_pam_record_inserts_row`
Expected: FAIL — `assert row["due_date"] == "2026-06-11"` fails because the function still stores the old `+1 month` value (`"2026-06-30"`).

- [ ] **Step 3: Fix all 6 call sites**

In `app/modules/payment_memo/service.py`, each of these 6 lines:

Line 627:
```python
        due_date = _add_one_month(tanggal)
```
becomes:
```python
        due_date = _workday(tanggal, 8).strftime("%Y-%m-%d")
```

Line 671:
```python
    due_date = _add_one_month(tanggal)
```
becomes:
```python
    due_date = _workday(tanggal, 8).strftime("%Y-%m-%d")
```

Line 751:
```python
        due_date = _add_one_month(tanggal)
```
becomes:
```python
        due_date = _workday(tanggal, 8).strftime("%Y-%m-%d")
```

Line 844:
```python
        due_date    = _add_one_month(tanggal)
```
becomes:
```python
        due_date    = _workday(tanggal, 8).strftime("%Y-%m-%d")
```

Line 925:
```python
    due_date    = _add_one_month(pam_date)
```
becomes:
```python
    due_date    = _workday(pam_date, 8).strftime("%Y-%m-%d")
```

Line 2441 (inside the tuple passed to `conn.execute`, currently):
```python
         _add_one_month(pam_date), ts)
```
becomes:
```python
         _workday(pam_date, 8).strftime("%Y-%m-%d"), ts)
```

Since lines 627/671/751/844 share the exact same old text (`due_date = _add_one_month(tanggal)`, differing only in surrounding whitespace/indentation), edit each one at its specific line number individually rather than a find-and-replace-all, to avoid accidentally skipping or double-editing due to non-unique matches.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_service.py -v -k test_create_pam_record_inserts_row`
Expected: PASS

- [ ] **Step 5: Add coverage for the other 5 call sites**

Check which existing tests exercise the other 5 functions (`save_klaim_payment` around line 627, the function at line 671, the one at line 751, `save_others_payment`/similar around line 844, and the one at line 2441 inside a PA-to-PAM cascade function) by running:

Run: `cd C:\Financehub\app && python -m pytest tests/test_pam_klaim.py tests/test_pam_pa_cascade.py tests/test_payment_memo_service.py -v`
Expected: PASS — these exercise the other insert functions but likely don't assert `due_date` values specifically (confirmed via earlier `grep -rn "due_date" tests/` — only `test_pam_service.py` had a `due_date` assertion before this task). Passing here means no regression; it does not yet prove the new formula is used in these 5 functions. If you want firmer coverage, add one assertion per test file mirroring Task 2 Step 1's pattern (call the function with a known `tanggal`/`pam_date`, assert the resulting `due_date` equals `_workday(that_date, 8).strftime("%Y-%m-%d")`) — this is optional hardening, not required to consider this task done, since the fix's shape (swap one function call for another, verified working in the one function with existing coverage) is mechanically identical across all 6 sites.

- [ ] **Step 6: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/service.py app/tests/test_pam_service.py
git commit -m "fix: store PAM due_date via WORKDAY+8 formula instead of +1 month"
```

---

### Task 3: New API endpoint + Input form Due Date field

**Files:**
- Modify: `app/modules/payment_memo/routes.py:5-30` (import), after `:166` (new route)
- Modify: `app/templates/payment_memo/index.html:185` (grid columns), `:219` (onchange), after `:220` (new field), `:4467-4491` (`ipayReset`), `:5473-5485` (remove `_calcSmtDueDate`), `:5583-5586` (`dueCell`)
- Test: `app/tests/test_payment_memo_ipay.py`

**Interfaces:**
- Consumes: `_workday` (Task 1)
- Produces: `GET /payment-memo/api/due-date?tanggal=YYYY-MM-DD` → `{"ok": true, "due_date": "YYYY-MM-DD"}`; JS function `ipayUpdateDueDate()` — sets `#ipay-due-date`'s value and updates every `.smt-due-cell`.

- [ ] **Step 1: Write the failing route test**

Check `app/tests/test_payment_memo_ipay.py` for its existing `login`/company-selection helpers (likely matching the `login`/`_select_etf` pattern used throughout this repo's tests) and add:

```python
def test_due_date_api_returns_workday_plus_8(client):
    login(client)
    _select_etf(client)
    resp = client.get("/payment-memo/api/due-date?tanggal=2026-07-06")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["due_date"] == "2026-07-16"


def test_due_date_api_rejects_missing_tanggal(client):
    login(client)
    _select_etf(client)
    resp = client.get("/payment-memo/api/due-date")
    assert resp.status_code == 400
```

(If `login`/`_select_etf` aren't already defined in this file, copy them verbatim from `app/tests/test_sponsorship_routes.py`'s versions — same pattern used across every route test file in this repo.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_payment_memo_ipay.py -v -k due_date_api`
Expected: FAIL with a 404 (route doesn't exist yet).

- [ ] **Step 3: Add the route**

In `app/modules/payment_memo/routes.py`, add `_workday` to the existing import block — replace:

```python
    get_advance_payments, realize_advance_payment,
)
```

with:

```python
    get_advance_payments, realize_advance_payment,
    _workday,
)
```

Add the new route after `list_coa()` (currently ending at line 166):

```python
@bp.route("/api/due-date")
@json_required
def get_due_date():
    tanggal = request.args.get("tanggal", "")
    if not tanggal:
        return jsonify({"ok": False, "pesan": "Parameter tanggal wajib diisi."}), 400
    try:
        due_date = _workday(tanggal, 8).strftime("%Y-%m-%d")
    except Exception:
        return jsonify({"ok": False, "pesan": "Format tanggal tidak valid."}), 400
    return jsonify({"ok": True, "due_date": due_date})
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_payment_memo_ipay.py -v -k due_date_api`
Expected: PASS (2 tests)

- [ ] **Step 5: Add the Due Date field to the Input form**

In `app/templates/payment_memo/index.html`, replace the shared header's grid declaration:

```html
    <div style="display:grid;grid-template-columns:{{ '160px 160px minmax(200px,1fr) 180px' if company_code == 'SMT' else '120px 150px 160px minmax(200px,1fr) 180px' }};gap:.75rem;margin-bottom:.5rem;align-items:end;max-width:980px">
```

with:

```html
    <div style="display:grid;grid-template-columns:{{ '160px 160px 130px minmax(200px,1fr) 180px' if company_code == 'SMT' else '120px 150px 160px 130px minmax(200px,1fr) 180px' }};gap:.75rem;margin-bottom:.5rem;align-items:end;max-width:1120px">
```

(One new `130px` track for Due Date in both variants; `max-width` widened from `980px` to `1120px` to fit it without shrinking the existing fields.)

Replace:

```html
      <div class="form-group" style="margin:0">
        <label>Tanggal</label>
        <input type="date" id="ipay-tgl" onchange="ipayFetchNextPamNo(); document.querySelectorAll('.smt-due-cell').forEach(el=>el.textContent=_calcSmtDueDate())">
      </div>
```

with:

```html
      <div class="form-group" style="margin:0">
        <label>Tanggal</label>
        <input type="date" id="ipay-tgl" onchange="ipayFetchNextPamNo(); ipayUpdateDueDate()">
      </div>
      <div class="form-group" style="margin:0">
        <label>Due Date</label>
        <input type="text" id="ipay-due-date" readonly placeholder="—"
               style="background:#f3f4f6;cursor:default;color:#374151;font-weight:600">
      </div>
```

- [ ] **Step 6: Add `ipayUpdateDueDate()`, remove `_calcSmtDueDate()`, repoint the per-row cell**

Replace:

```javascript
function _calcSmtDueDate() {
  const tgl = document.getElementById("ipay-tgl")?.value;
  if (!tgl) return "-";
  let d = new Date(tgl);
  if (isNaN(d.getTime())) return "-";
  let added = 0;
  while (added < 8) {
    d.setDate(d.getDate() + 1);
    const day = d.getDay();
    if (day !== 0 && day !== 6) added++;
  }
  return d.toISOString().split('T')[0];
}
```

with:

```javascript
async function ipayUpdateDueDate() {
  const tgl = document.getElementById("ipay-tgl")?.value;
  const dueField = document.getElementById("ipay-due-date");
  if (!dueField) return;
  if (!tgl) { dueField.value = ""; return; }
  try {
    const res = await apiFetch(`/payment-memo/api/due-date?tanggal=${tgl}`);
    const data = res ? await res.json() : null;
    dueField.value = (data && data.ok) ? data.due_date : "-";
  } catch (e) {
    dueField.value = "-";
  }
  document.querySelectorAll(".smt-due-cell").forEach(el => el.textContent = dueField.value);
}
```

Replace:

```javascript
  const dueCell = document.createElement("div");
  dueCell.className = "smt-due-cell";
  dueCell.style.cssText = "font-family:monospace;font-size:11px;color:#4b5563;white-space:nowrap;padding-top:6px;text-align:center";
  dueCell.textContent = _calcSmtDueDate();
```

with:

```javascript
  const dueCell = document.createElement("div");
  dueCell.className = "smt-due-cell";
  dueCell.style.cssText = "font-family:monospace;font-size:11px;color:#4b5563;white-space:nowrap;padding-top:6px;text-align:center";
  dueCell.textContent = document.getElementById("ipay-due-date")?.value || "-";
```

- [ ] **Step 7: Trigger the initial calculation on form reset**

In `ipayReset()`, replace:

```javascript
  document.getElementById("ipay-tgl").value = new Date().toISOString().slice(0, 10);
```

with:

```javascript
  document.getElementById("ipay-tgl").value = new Date().toISOString().slice(0, 10);
  ipayUpdateDueDate();
```

- [ ] **Step 8: Run the Input-tab test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_payment_memo_ipay.py tests/test_pam_smt_lines_routes.py -v`
Expected: all PASS.

- [ ] **Step 9: Manual check**

Open PAM → Input for ETF (any pillar) and for SMT. Change "Tanggal" and confirm "Due Date" populates a moment later with the WORKDAY+8 value. Add a row in the SMT GL/Advance panel and confirm its own due-date column matches the shared field.

- [ ] **Step 10: Commit**

```bash
cd C:\Financehub
git add app/modules/payment_memo/routes.py app/templates/payment_memo/index.html app/tests/test_payment_memo_ipay.py
git commit -m "feat: add live Due Date field to PAM Input form for all pillars"
```

---

### Task 4: Visual redesign — color-coded sections

**Files:**
- Modify: `app/templates/payment_memo/index.html:185, 243, 261, 299, 338, 390`

**Interfaces:**
- Consumes: `.form-section`, `.form-section-title`, `.tint-jenis`, `.tint-route`, `.tint-pay` CSS classes (already shipped in `style.css` by the ETF PA Input redesign — no new CSS needed).

- [ ] **Step 1: Tint the two shared header rows**

Replace (the grid div from Task 3 Step 5, now with the Due Date column already added):

```html
    <div style="display:grid;grid-template-columns:{{ '160px 160px 130px minmax(200px,1fr) 180px' if company_code == 'SMT' else '120px 150px 160px 130px minmax(200px,1fr) 180px' }};gap:.75rem;margin-bottom:.5rem;align-items:end;max-width:1120px">
```

with:

```html
    <div class="form-section tint-jenis" style="display:grid;grid-template-columns:{{ '160px 160px 130px minmax(200px,1fr) 180px' if company_code == 'SMT' else '120px 150px 160px 130px minmax(200px,1fr) 180px' }};gap:.75rem;margin-bottom:.5rem;align-items:end;max-width:1120px">
```

Replace:

```html
    <div style="display:grid;grid-template-columns:200px 140px 1fr;gap:.75rem;margin-bottom:1rem;align-items:end;max-width:900px">
```

with:

```html
    <div class="form-section tint-route" style="display:grid;grid-template-columns:200px 140px 1fr;gap:.75rem;margin-bottom:1rem;align-items:end;max-width:900px">
```

- [ ] **Step 2: Tint the 4 transaction panels**

Replace:

```html
    <div id="ipay-panel-beasiswa">
```

with:

```html
    <div id="ipay-panel-beasiswa" class="form-section tint-pay">
```

Replace:

```html
<div id="ipay-panel-klaim" style="display:none">
```

with:

```html
<div id="ipay-panel-klaim" class="form-section tint-pay" style="display:none">
```

Replace:

```html
<div id="ipay-panel-others" style="display:none">
```

with:

```html
<div id="ipay-panel-others" class="form-section tint-pay" style="display:none">
```

Replace:

```html
<div id="ipay-panel-smt-lines" style="display:none">
```

with:

```html
<div id="ipay-panel-smt-lines" class="form-section tint-pay" style="display:none">
```

- [ ] **Step 3: Run the Input-tab test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_payment_memo_ipay.py -v`
Expected: PASS — this is presentation-only, no assertion in this file should reference the removed inline styles (verify by reading test output; if any test asserts exact markup this task's diff intersects, update its expectation, but none are expected here since these tests target route/behavior, not raw HTML structure).

- [ ] **Step 4: Manual check**

Open PAM → Input. Confirm: Identitas PAM row (Tipe/Transaksi/Tanggal/Due Date/No. PAM/Perusahaan) has a blue tint; Metadata Auto row (Pillar/CC/Catatan) has a violet tint; whichever transaction panel is active (switch "Transaksi" dropdown to see each) has an orange/tangerine tint. Confirm no field moved, reordered, or changed size beyond the new Due Date column from Task 3.

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/templates/payment_memo/index.html
git commit -m "style: apply color-coded form-section tints to PAM Input form"
```

---

### Task 5: Migrate existing PAM records' due dates

**Files:**
- Create: `scripts/migrate_pam_due_dates.py`
- Test: `app/tests/test_migrate_pam_due_dates.py`

**Interfaces:**
- Consumes: `_workday` (Task 1)

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_migrate_pam_due_dates.py`:

```python
import os
import sys
import subprocess
import sqlite3

import config


def test_migration_updates_stale_due_dates(tmp_path):
    db_path = str(tmp_path / "migrate_test.db")
    from database import init_db
    old_db_path = config.DB_PATH
    config.DB_PATH = db_path
    try:
        init_db()
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO pam_records
               (company_id, pam_no, pam_date, requestors_name, keterangan,
                total_amount, due_date, pillar, source, status, created_at)
               VALUES (2, 'PAM-TEST-01', '2026-05-31', 'Jany Turkanda', 'test',
                       1000000, '2026-06-30', 'AGRI', 'beasiswa', 'open', '2026-05-31T00:00:00')"""
        )
        conn.commit()
        conn.close()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script = os.path.join(os.path.dirname(base_dir), "scripts", "migrate_pam_due_dates.py")
        result = subprocess.run(
            [sys.executable, script, "--db-path", db_path, "--skip-backup"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT due_date FROM pam_records WHERE pam_no='PAM-TEST-01'").fetchone()
        conn.close()
        assert row[0] == "2026-06-11"
    finally:
        config.DB_PATH = old_db_path
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_migrate_pam_due_dates.py -v`
Expected: FAIL — `scripts/migrate_pam_due_dates.py` doesn't exist yet.

- [ ] **Step 3: Write the migration script**

Create `scripts/migrate_pam_due_dates.py`:

```python
import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_dir = os.path.join(base_dir, "app")
sys.path.insert(0, app_dir)

from modules.payment_memo.service import _workday


def migrate(db_path: str, skip_backup: bool) -> None:
    if not skip_backup:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.bak_before_due_date_migration_{ts}"
        shutil.copy2(db_path, backup_path)
        print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id, pam_date, due_date FROM pam_records").fetchall()

    updated = 0
    unchanged = 0
    for pam_id, pam_date, old_due_date in rows:
        try:
            new_due_date = _workday(pam_date, 8).strftime("%Y-%m-%d")
        except Exception as e:
            print(f"Skipping pam_records.id={pam_id}: could not compute due_date from pam_date={pam_date!r} ({e})")
            continue
        if new_due_date != old_due_date:
            conn.execute("UPDATE pam_records SET due_date = ? WHERE id = ?", (new_due_date, pam_id))
            updated += 1
        else:
            unchanged += 1
    conn.commit()
    conn.close()

    print(f"Migration complete: {updated} row(s) updated, {unchanged} row(s) already correct.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default=None, help="Override the database path (defaults to config.DB_PATH)")
    parser.add_argument("--skip-backup", action="store_true", help="Skip creating a .bak copy first (used by tests)")
    args = parser.parse_args()

    if args.db_path:
        db_path = args.db_path
    else:
        import config
        db_path = config.DB_PATH

    migrate(db_path, args.skip_backup)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_migrate_pam_due_dates.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add scripts/migrate_pam_due_dates.py app/tests/test_migrate_pam_due_dates.py
git commit -m "feat: add migration script to recompute existing PAM due dates"
```

- [ ] **Step 6: Run the migration against the real database**

This writes real changes to `C:\Financehub\app\finance_hub.db` — confirm with the user before running unattended.

Run: `cd C:\Financehub && python scripts\migrate_pam_due_dates.py`
Expected: prints a backup path, then `Migration complete: N row(s) updated, M row(s) already correct.` Spot-check a few updated PAMs in the app (Payment Approval Memo tabs) to confirm their due dates now match what printing that same PAM shows.

---

### Task 6: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/ -q`
Expected: same pass/fail counts as before this plan, aside from the tests this plan added/fixed (pre-existing failures are documented as unrelated Windows SQLite file-lock flakiness in `01 - Proyek/FinanceHub/FinanceHub - Known Issues.md` in the Obsidian vault).

- [ ] **Step 2: Confirm scope**

Run: `cd C:\Financehub && git log --oneline -8`
Expected: 5 commits from this plan (Tasks 1-5), each with the message from its own Step 5/6/etc. above.

- [ ] **Step 3: Report status to the user**

Summarize: due date now computed by one formula everywhere (stored, printed, and previewed live for every pillar), existing PAM records migrated, Input form re-tinted to match the PA Input redesign with no layout changes — ready for a final visual pass in the browser.
