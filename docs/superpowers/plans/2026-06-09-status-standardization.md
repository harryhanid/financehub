# Status Standardization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename all status strings across payment_beasiswa, payment_memo, pam_records, and payment_application to the uniform `open → on_process → complete` model.

**Architecture:** Single-pass — run a Python migration script to backup and UPDATE live DB, then update every string literal in services, routes, templates, and tests. No new logic. Pure value rename.

**Spec:** `docs/superpowers/specs/2026-06-09-status-standardization.md`

**Tech Stack:** Python/Flask, SQLite, Jinja2

---

## Files Modified

| File | What changes |
|------|-------------|
| `app/migrate_status.py` | NEW — DB backup + UPDATE script |
| `app/modules/payment_memo/service.py` | 12 status string changes |
| `app/modules/payment_memo/routes.py` | 1 gate check: `"paid"` → `"complete"` |
| `app/modules/payment_memo/api.py` | 1 filter: `'draft'` → `'open'` |
| `app/modules/payment_application/service.py` | 3 changes |
| `app/modules/payment_application/routes.py` | 1 filter: `"approved"` → `"on_process"` |
| `app/modules/beasiswa/service.py` | 3 guard fixes |
| `app/modules/dashboard/routes.py` | 1 stat query |
| `app/database.py` | 4 DEFAULT changes |
| `app/templates/payment_memo/index.html` | JS badge/status maps |
| `app/templates/payment_application/index.html` | Badge class + label |
| `app/templates/beasiswa/index.html` | JS badge map + filter options |
| `app/tests/test_payment_memo_service.py` | 1 assertion + 2 fixtures |
| `app/tests/test_beasiswa_service.py` | 2 assertions |
| `app/tests/test_pam_service.py` | 3 fixtures + 2 assertions |
| `app/tests/test_pam_pa_cascade.py` | 3 fixtures |
| `app/tests/test_payment_memo_ipay.py` | 2 INSERT fixtures |
| `app/tests/test_pam_exports.py` | 3 INSERT fixtures |
| `app/tests/test_memo_api.py` | 1 INSERT fixture |

---

### Task 1: Create and run DB migration script

**Files:**
- Create: `app/migrate_status.py`

- [ ] **Step 1: Create `app/migrate_status.py`**

```python
#!/usr/bin/env python3
"""
migrate_status.py — Standardize all status values to open/on_process/complete.
Run from the project root: python app/migrate_status.py
"""
import os
import shutil
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "finance_hub.db")


def main():
    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{DB_PATH}.bak_status_{ts}"
    shutil.copy2(DB_PATH, backup)
    print(f"Backup: {backup}")

    migrations = [
        # payment_beasiswa
        "UPDATE payment_beasiswa SET status='open'       WHERE status='draft'",
        "UPDATE payment_beasiswa SET status='on_process' WHERE status='in_memo'",
        "UPDATE payment_beasiswa SET status='complete'   WHERE status='paid'",
        # payment_memo
        "UPDATE payment_memo SET status='open'       WHERE status='draft'",
        "UPDATE payment_memo SET status='on_process' WHERE status='approved'",
        "UPDATE payment_memo SET status='complete'   WHERE status='paid'",
        # pam_records
        "UPDATE pam_records SET status='open'       WHERE status='draft'",
        "UPDATE pam_records SET status='on_process' WHERE status='approved'",
        "UPDATE pam_records SET status='complete'   WHERE status='paid'",
        # payment_application
        "UPDATE payment_application SET status='open'     WHERE status='pending'",
        "UPDATE payment_application SET status='complete' WHERE status='completed'",
    ]

    conn = sqlite3.connect(DB_PATH)
    try:
        for sql in migrations:
            cur = conn.execute(sql)
            print(f"  {cur.rowcount:4d} rows — {sql}")
        conn.commit()
        print("\nDone.")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}\nRolled back. Restore from {backup} if needed.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the migration**

```
cd C:\Financehub
python app/migrate_status.py
```

Expected output (row counts will vary):
```
Backup: app/finance_hub.db.bak_status_20260609_...
  1273 rows — UPDATE payment_beasiswa SET status='open' WHERE status='draft'
     0 rows — UPDATE payment_beasiswa SET status='on_process' WHERE status='in_memo'
     0 rows — UPDATE payment_beasiswa SET status='complete' WHERE status='paid'
   ...
Done.
```

- [ ] **Step 3: Verify spot-check**

```
python -c "
import sqlite3, os
conn = sqlite3.connect('app/finance_hub.db')
for tbl in ['payment_beasiswa','payment_memo','pam_records','payment_application']:
    rows = conn.execute(f'SELECT status, COUNT(*) FROM {tbl} GROUP BY status').fetchall()
    print(tbl, dict(rows))
conn.close()
"
```

Expected: no `draft`, `in_memo`, `approved`, `paid`, `pending`, `completed` values remaining.

- [ ] **Step 4: Commit**

```bash
git add app/migrate_status.py
git commit -m "feat: add DB migration script for status standardization"
```

---

### Task 2: Update `payment_memo/service.py` — core status strings

**Files:**
- Modify: `app/modules/payment_memo/service.py`

- [ ] **Step 1: Fix `get_draft_payments()` SQL (line 37)**

Change:
```python
WHERE pb.company_id = ? AND pb.status = 'draft'
```
To:
```python
WHERE pb.company_id = ? AND pb.status = 'open'
```

- [ ] **Step 2: Fix `create_memo()` INSERT + UPDATE (lines ~56, ~76)**

In the INSERT, change `'draft'` → `'open'`:
```python
"""INSERT INTO payment_memo
   (company_id, memo_number, tanggal, total_amount, status, notes, created_by, created_at)
   VALUES (?,?,?,?,'open',?,?,?)"""
```

In the UPDATE payment_beasiswa inside create_memo, change `'in_memo'` → `'on_process'`:
```python
"UPDATE payment_beasiswa SET status='on_process', memo_id=? WHERE id=?"
```

- [ ] **Step 3: Fix `update_memo_status()` (lines ~119–148)**

Change allowed set:
```python
allowed = {"open", "on_process", "complete"}
```

Change the cascade block:
```python
if new_status == "complete":
    conn.execute(
        "UPDATE payment_beasiswa SET status='complete' WHERE memo_id=?",
        (memo_id,)
    )
elif new_status in ("open", "on_process"):
    # Revert payment_beasiswa saat memo diturunkan statusnya
    conn.execute(
        "UPDATE payment_beasiswa SET status='open' WHERE memo_id=? AND status='complete'",
        (memo_id,)
    )
```

- [ ] **Step 4: Fix `set_memo_tanggal_bayar()` beasiswa cascade (line ~182)**

Change:
```python
"UPDATE payment_beasiswa SET status='paid' WHERE memo_id=?",
```
To:
```python
"UPDATE payment_beasiswa SET status='complete' WHERE memo_id=?",
```

- [ ] **Step 5: Fix `create_pam_record()` INSERT (line ~360)**

Change `'draft'` → `'open'`:
```python
"""INSERT INTO pam_records
   (company_id, pam_no, pam_date, gl_account, cost_center, pt,
    requestors_name, keterangan, total_amount, due_date, status, created_at)
   VALUES (?,?,?,?,?,?,?,?,?,?,'open',?)"""
```

- [ ] **Step 6: Fix `update_pam_status()` allowed set (line ~441)**

```python
allowed = {"open", "on_process", "complete"}
```

- [ ] **Step 7: Fix `delete_payment_beasiswa()` guard (line ~498)**

```python
if row["status"] != "open":
    conn.close()
    return {"ok": False, "pesan": "Hanya payment berstatus open yang bisa dihapus."}
```

- [ ] **Step 8: Fix `save_pa_payment()` pam_records INSERT (line ~292)**

```python
"""INSERT INTO pam_records
   (company_id, pam_no, pam_date, requestors_name, keterangan,
    total_amount, due_date, source, status, created_at)
   VALUES (?,?,?,?,?,?,?,?,'open',?)"""
```

- [ ] **Step 9: Fix `create_pam_from_etf_pa()` pam_records INSERT (line ~1364)**

```python
"""INSERT INTO pam_records
   (company_id, pam_no, pam_date, gl_account, cost_center, pt,
    requestors_name, keterangan, total_amount, due_date, status, source, created_at)
   VALUES (?,?,?,?,?,?,?,?,?,?,'open','etf_agri',?)"""
```

- [ ] **Step 10: Fix `set_pam_tanggal_bayar_agri()` pam UPDATE (line ~1409)**

```python
"UPDATE pam_records SET tanggal_bayar=?, status='complete', updated_at=? WHERE id=?"
```

- [ ] **Step 11: Fix `update_sml_status()` allowed set (line ~1209)**

```python
_ALLOWED = {"open", "on_process", "complete"}
```

- [ ] **Step 12: Fix `update_fiori_status()` allowed set (line ~1181)**

```python
_ALLOWED = {"open", "on_process", "complete"}
```

- [ ] **Step 13: Run existing tests (will fail until Task 8)**

```
cd C:\Financehub\app
python -m pytest tests/test_payment_memo_service.py tests/test_pam_service.py -v 2>&1 | head -40
```

Expected: some tests fail on status assertions — that's expected at this stage.

- [ ] **Step 14: Commit**

```bash
git add app/modules/payment_memo/service.py
git commit -m "refactor: standardize status strings in payment_memo/service.py"
```

---

### Task 3: Small service/route changes (3 files)

**Files:**
- Modify: `app/modules/payment_memo/routes.py`
- Modify: `app/modules/payment_memo/api.py`
- Modify: `app/modules/dashboard/routes.py`

- [ ] **Step 1: Fix `payment_memo/routes.py` role gate (line ~118)**

Change:
```python
if new_status == "paid" and claims.get("role") != "releaser":
    return jsonify({"ok": False, "pesan": "Hanya Releaser yang dapat mark as Paid."}), 403
```
To:
```python
if new_status == "complete" and claims.get("role") != "releaser":
    return jsonify({"ok": False, "pesan": "Hanya Releaser yang dapat mark as Complete."}), 403
```

- [ ] **Step 2: Fix `payment_memo/api.py` status filter (line ~98)**

Change `pb.status='draft'` → `pb.status='open'` in the SQL WHERE clause.

- [ ] **Step 3: Fix `dashboard/routes.py` stat query (line 72)**

Change:
```python
"SELECT COUNT(*) FROM payment_memo WHERE company_id = ? AND status = 'draft'", (company_id,)
```
To:
```python
"SELECT COUNT(*) FROM payment_memo WHERE company_id = ? AND status = 'open'", (company_id,)
```

- [ ] **Step 4: Commit**

```bash
git add app/modules/payment_memo/routes.py app/modules/payment_memo/api.py app/modules/dashboard/routes.py
git commit -m "refactor: status strings in routes and dashboard"
```

---

### Task 4: Update `payment_application` module

**Files:**
- Modify: `app/modules/payment_application/service.py`
- Modify: `app/modules/payment_application/routes.py`

- [ ] **Step 1: Fix `create_application()` INSERT status (service.py line ~67)**

Change `'pending'` → `'open'`:
```python
cur = conn.execute(
    """INSERT INTO payment_application
       (company_id, memo_id, application_number, submitted_at, target_payment_date, notes, status, created_at)
       VALUES (?,?,?,?,?,?,'open',?)""",
    ...
)
```

- [ ] **Step 2: Fix `create_application()` gate check (service.py line ~58)**

Change:
```python
if memo["status"] not in ("approved", "paid"):
    conn.close()
    return {"ok": False, "pesan": "Memo harus berstatus 'approved' sebelum diajukan."}
```
To:
```python
if memo["status"] not in ("on_process", "complete"):
    conn.close()
    return {"ok": False, "pesan": "Memo harus berstatus 'on_process' atau 'complete' sebelum diajukan."}
```

- [ ] **Step 3: Fix `update_actual_payment()` status (service.py line ~94)**

Change:
```python
conn.execute(
    "UPDATE payment_application SET actual_payment_date=?, tat_days=?, status='completed', updated_at=? WHERE id=? AND company_id=?",
    ...
)
```
To:
```python
conn.execute(
    "UPDATE payment_application SET actual_payment_date=?, tat_days=?, status='complete', updated_at=? WHERE id=? AND company_id=?",
    ...
)
```

- [ ] **Step 4: Fix `routes.py` memo filter (line ~35)**

Change:
```python
approved_memos = [m for m in get_memo_list(company_id, status="approved")
```
To:
```python
approved_memos = [m for m in get_memo_list(company_id, status="on_process")
```

- [ ] **Step 5: Commit**

```bash
git add app/modules/payment_application/service.py app/modules/payment_application/routes.py
git commit -m "refactor: status strings in payment_application module"
```

---

### Task 5: Fix dead-code guards in `beasiswa/service.py`

**Files:**
- Modify: `app/modules/beasiswa/service.py`

These three guards check `status == "approved"` — a value that never existed in `payment_beasiswa`. With the new model, the intent is to block deletion of payments that are already finished (`complete`).

- [ ] **Step 1: Fix deletion guard ~line 658**

Change:
```python
if row["status"] == "approved":
    conn.close()
    return {"ok": False, "pesan": "Payment yang sudah approved tidak bisa dihapus."}
```
To:
```python
if row["status"] == "complete":
    conn.close()
    return {"ok": False, "pesan": "Payment yang sudah selesai tidak bisa dihapus."}
```

- [ ] **Step 2: Fix deletion guard ~line 722**

Same pattern — change `"approved"` → `"complete"` and update the message identically.

- [ ] **Step 3: Fix klaim deletion guard ~line 960**

Change:
```python
if pay and pay["status"] == "approved":
    conn.close()
    return {"ok": False, "pesan": "Klaim yang sudah approved tidak bisa dihapus."}
```
To:
```python
if pay and pay["status"] == "complete":
    conn.close()
    return {"ok": False, "pesan": "Klaim yang sudah selesai tidak bisa dihapus."}
```

- [ ] **Step 4: Commit**

```bash
git add app/modules/beasiswa/service.py
git commit -m "fix: deletion guards use 'complete' instead of dead 'approved' status"
```

---

### Task 6: Update `database.py` DEFAULT values

**Files:**
- Modify: `app/database.py`

Change `DEFAULT 'draft'` → `DEFAULT 'open'` for the four tables in scope. The PA tables (`etf_pa`, `app_pa`, `sml_pa`, `setf_pa`) already default to `'open'` — don't touch those.

- [ ] **Step 1: Identify and update `payment_beasiswa` DEFAULT**

Find the line: `status       TEXT DEFAULT 'draft',` inside the `payment_beasiswa` CREATE TABLE block.
Change to: `status       TEXT DEFAULT 'open',`

- [ ] **Step 2: Update `payment_memo` DEFAULT**

Find: `status          TEXT DEFAULT 'draft',` inside `payment_memo` CREATE TABLE.
Change to: `status          TEXT DEFAULT 'open',`

- [ ] **Step 3: Update `pam_records` DEFAULT**

Find: `status                   TEXT NOT NULL DEFAULT 'draft',` inside `pam_records` CREATE TABLE.
Change to: `status                   TEXT NOT NULL DEFAULT 'open',`

- [ ] **Step 4: Update `payment_application` DEFAULT**

Find: `status          TEXT DEFAULT 'draft',` inside `payment_application` CREATE TABLE.
Change to: `status          TEXT DEFAULT 'open',`

- [ ] **Step 5: Commit**

```bash
git add app/database.py
git commit -m "refactor: schema DEFAULT 'draft' → 'open' for payment tables"
```

---

### Task 7: Update templates

**Files:**
- Modify: `app/templates/payment_memo/index.html`
- Modify: `app/templates/payment_application/index.html`
- Modify: `app/templates/beasiswa/index.html`

- [ ] **Step 1: Fix `payment_memo/index.html` — JS status label map (line ~792)**

Change:
```javascript
const label = { submitted: "Submit", approved: "Approve", paid: "Mark as Paid", on_process: "Submit / Proses" }[newStatus] || newStatus;
```
To:
```javascript
const label = { submitted: "Submit", on_process: "Submit / Proses", complete: "Mark as Complete" }[newStatus] || newStatus;
```

- [ ] **Step 2: Fix `payment_memo/index.html` — SML badge class map (line ~894)**

Change:
```javascript
const stCls = {open:'badge-gray', approved:'badge-green', paid:'badge-blue'}[st] || 'badge-gray';
```
To:
```javascript
const stCls = {open:'badge-gray', on_process:'badge-green', complete:'badge-blue'}[st] || 'badge-gray';
```

- [ ] **Step 3: Fix `payment_memo/index.html` — SML status action buttons (lines ~897–899)**

Change:
```javascript
aksi += `<button class="btn btn-sm btn-success" onclick="smlUpdateStatus(${r.id},'approved')">Approve</button>`;
else if (st === 'approved')
```
To:
```javascript
aksi += `<button class="btn btn-sm btn-success" onclick="smlUpdateStatus(${r.id},'on_process')">Process</button>`;
else if (st === 'on_process')
```

Then find the next action in the same block. If it was `paid`, change to `complete`:
```javascript
aksi += `<button class="btn btn-sm btn-primary" onclick="smlUpdateStatus(${r.id},'complete')">Complete</button>`;
```

- [ ] **Step 4: Fix `payment_application/index.html` — badge class (line ~102)**

Change:
```html
<span class="badge {% if a.status == 'completed' %}badge-green{% elif a.status == 'pending' %}badge-yellow{% else %}badge-gray{% endif %}">
```
To:
```html
<span class="badge {% if a.status == 'complete' %}badge-green{% elif a.status == 'open' %}badge-yellow{% else %}badge-gray{% endif %}">
```

- [ ] **Step 5: Fix `payment_application/index.html` — form label (line ~130)**

Change:
```html
<label>Pilih Memo (status: approved)</label>
```
To:
```html
<label>Pilih Memo (status: on_process)</label>
```

- [ ] **Step 6: Fix `beasiswa/index.html` — filter select options (line ~432–433)**

Change:
```html
<option value="approved">Approved</option>
<option value="draft">Draft</option>
```
To:
```html
<option value="on_process">On Process</option>
<option value="open">Open</option>
<option value="complete">Complete</option>
```

- [ ] **Step 7: Fix `beasiswa/index.html` — JS badge maps (lines ~1271–1272 and ~1566–1567)**

For BOTH badge map objects in beasiswa/index.html, change:
```javascript
approved: `<span style="background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">Approved</span>`,
draft:    `<span style="background:#fef3c7;color:#d97706;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">Draft</span>`,
```
To:
```javascript
on_process: `<span style="background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">On Process</span>`,
open:       `<span style="background:#fef3c7;color:#d97706;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">Open</span>`,
complete:   `<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">Complete</span>`,
```

- [ ] **Step 8: Commit**

```bash
git add app/templates/payment_memo/index.html app/templates/payment_application/index.html app/templates/beasiswa/index.html
git commit -m "refactor: update status badge labels and maps in templates"
```

---

### Task 8: Update tests

**Files:**
- Modify: `app/tests/test_payment_memo_service.py`
- Modify: `app/tests/test_beasiswa_service.py`
- Modify: `app/tests/test_pam_service.py`
- Modify: `app/tests/test_pam_pa_cascade.py`
- Modify: `app/tests/test_payment_memo_ipay.py`
- Modify: `app/tests/test_pam_exports.py`
- Modify: `app/tests/test_memo_api.py`

- [ ] **Step 1: `test_payment_memo_service.py`**

Line 28 in `_add_draft_payment()` helper — change INSERT fixture:
```python
"VALUES (?,?,?,?,?,?,?,?,'open')",
```

Lines 42 and 44 — pam fixture INSERTs:
```python
(COMPANY_ID, "PAM/ETF/2025/001", "open")
(COMPANY_ID, "PAM/ETF/2025/002", "open")
```

Line 77 — assertion:
```python
assert row["status"] == "on_process"
```

- [ ] **Step 2: `test_beasiswa_service.py`**

Line 117:
```python
assert row["status"] == "open"
```

Line 168:
```python
assert pay["status"] == "open"
```

- [ ] **Step 3: `test_pam_service.py`**

Line 80:
```python
assert row["status"] == "open"
```

Line 91 — INSERT fixture:
```python
(COMPANY_ID, "S001", "By Pendidikan", "Semester 1", "2026-05-31", 2000000, "AGRI", "PT. SMART Tbk", "open")
```

Line 146 — rename test function (optional but clear):
```python
def test_update_pam_status_on_process():
```

Line 157:
```python
result = update_pam_status(pam_id, "on_process", COMPANY_ID)
```

Line 162:
```python
assert row["status"] == "on_process"
```

Line 237 — payment_beasiswa fixture:
```python
5000000, "ETF", "PT. SMART Tbk", pam_no, "open")
```

- [ ] **Step 4: `test_pam_pa_cascade.py`**

Line 71 — payment_beasiswa INSERT:
```python
VALUES (?,?,?,?,?,?,?,?,?,?,'on_process')""",
```

Line 141 — pam_records INSERT:
```python
(COMPANY_ID, pam_no, "2026-06-08", 5000000, "open", _ts())
```

Line 152 — payment_beasiswa INSERT:
```python
VALUES (?,?,?,?,?,?,?,?,?,?,'open')""",
```

- [ ] **Step 5: `test_payment_memo_ipay.py`**

Lines 95–96 — pam_records INSERTs:
```python
conn.execute("INSERT INTO pam_records (company_id,pam_no,source,status,created_at) VALUES (1,'PAM-001-ETF-06-2026','etf_agri','open','2026-06-08')")
conn.execute("INSERT INTO pam_records (company_id,pam_no,source,status,created_at) VALUES (1,'PAM-001-APP-06-2026','etf_app','open','2026-06-08')")
```

- [ ] **Step 6: `test_pam_exports.py`**

Line 30 — pam_records INSERT:
```python
VALUES (?,?,?,?,?,?,?,?,?,?,'open',?)""",
```

Line 48 — payment_beasiswa INSERT:
```python
5000000, "ETF", "PT. SMART Tbk", "PAM-001-ETF-05-2026", "open")
```

Line 212 — payment_beasiswa INSERT:
```python
(COMPANY_ID, "S002", cat1, cat2, "2026-05-26", amt, PAM_NO, "open")
```

- [ ] **Step 7: `test_memo_api.py`**

Line 127 — payment_beasiswa INSERT:
```python
(2, "S001", "General", "Sem 1", "2026-05-31", 5000000, "ETF", "PT. SMART Tbk", pam_no, "open"),
```

- [ ] **Step 8: Commit**

```bash
git add app/tests/
git commit -m "test: update fixtures and assertions to new open/on_process/complete statuses"
```

---

### Task 9: Run full test suite and verify

**Files:** None — verification only

- [ ] **Step 1: Run full test suite**

```
cd C:\Financehub\app
python -m pytest tests/ -v 2>&1 | tail -30
```

Expected: All tests pass. If failures remain, check which assertion still uses an old status string.

- [ ] **Step 2: Check for any remaining old status literals in Python**

```
grep -r "status.*'draft'\|status.*'in_memo'\|status.*'approved'\|status.*'paid'\|status.*'pending'\|status.*'completed'" app/modules/ --include="*.py"
```

Expected: zero matches (aside from comments or column names that legitimately use these words).

- [ ] **Step 3: Check for any remaining old status literals in templates**

```
grep -rn "value=\"draft\"\|value=\"approved\"\|value=\"paid\"\|value=\"pending\"\|value=\"completed\"\|status.*draft\|status.*in_memo" app/templates/ --include="*.html"
```

Review any matches to confirm they are intentional or stale.

- [ ] **Step 4: Final commit if any straggler fixes needed**

```bash
git add -p
git commit -m "fix: remaining stale status strings after standardization"
```
