# Status Standardization — All Modules

**Date:** 2026-06-09  
**Scope:** payment_beasiswa, payment_memo, pam_records, payment_application  
**Approach:** Single-pass migration (backup → SQL → code)

---

## Goal

Standardize all status progressions to a single, consistent model:

```
open → on_process → complete
```

This replaces the current mixed vocabulary (`draft`, `in_memo`, `approved`, `paid`, `pending`, `completed`) across tables.

---

## Status Mapping

### DB Tables

| Table | `draft` | `in_memo` | `approved` | `paid` | `pending` | `completed` |
|-------|---------|-----------|------------|--------|-----------|-------------|
| `payment_beasiswa` | → `open` | → `on_process` | → `on_process` | → `complete` | — | — |
| `payment_memo` | → `open` | — | → `on_process` | → `complete` | — | — |
| `pam_records` | → `open` | — | → `on_process` | → `complete` | — | — |
| `payment_application` | — | — | — | — | → `open` | → `complete` |
| `etf_pa`, `app_pa`, `sml_pa`, `setf_pa` | ✓ already correct | — | — | — | — | — |

### State Semantics

| Status | Meaning |
|--------|---------|
| `open` | Newly created, not yet in any processing flow |
| `on_process` | Attached to memo/PAM, being processed |
| `complete` | Paid/finished |

---

## Migration Script

**File:** `app/migrate_status.py`

Sequence:
1. Auto-backup DB to `finance_hub.db.bak_status_YYYYMMDD_HHMMSS`
2. Run all UPDATEs in a single SQLite transaction
3. Print row count changed per statement
4. Commit on success; rollback and print error on failure

```sql
-- payment_beasiswa
UPDATE payment_beasiswa SET status='open'       WHERE status='draft';
UPDATE payment_beasiswa SET status='on_process' WHERE status='in_memo';
UPDATE payment_beasiswa SET status='complete'   WHERE status='paid';

-- payment_memo
UPDATE payment_memo SET status='open'       WHERE status='draft';
UPDATE payment_memo SET status='on_process' WHERE status='approved';
UPDATE payment_memo SET status='complete'   WHERE status='paid';

-- pam_records
UPDATE pam_records SET status='open'       WHERE status='draft';
UPDATE pam_records SET status='on_process' WHERE status='approved';
UPDATE pam_records SET status='complete'   WHERE status='paid';

-- payment_application
UPDATE payment_application SET status='open'     WHERE status='pending';
UPDATE payment_application SET status='complete' WHERE status='completed';
```

---

## Code Changes

### `app/modules/payment_memo/service.py`

| Location | Old | New |
|----------|-----|-----|
| `get_draft_payments()` SQL | `status = 'draft'` | `status = 'open'` |
| `create_memo()` INSERT | `'draft'` | `'open'` |
| `create_memo()` UPDATE beasiswa | `status='in_memo'` | `status='on_process'` |
| `update_memo_status()` allowed set | `{"draft","on_process","complete"}` | `{"open","on_process","complete"}` |
| `update_memo_status()` revert beasiswa | `status='draft'` | `status='open'` |
| `update_memo_status()` revert condition | `in ("draft","on_process")` | `in ("open","on_process")` |
| `update_memo_status()` complete cascade | `status='paid'` | `status='complete'` |
| `set_memo_tanggal_bayar()` beasiswa cascade | `status='paid'` | `status='complete'` |
| `create_pam_record()` INSERT | `'draft'` | `'open'` |
| `update_pam_status()` allowed set | `{"draft","approved","paid"}` | `{"open","on_process","complete"}` |
| `delete_payment_beasiswa()` guard | `!= "draft"` | `!= "open"` |
| `save_pa_payment()` pam_records INSERT | `'draft'` | `'open'` |
| `create_pam_from_etf_pa()` pam_records INSERT | `'draft'` | `'open'` |
| `set_pam_tanggal_bayar_agri()` pam UPDATE | `status='paid'` | `status='complete'` |

### `app/modules/payment_memo/routes.py`

| Location | Old | New |
|----------|-----|-----|
| `update_status()` role gate | `new_status == "paid"` | `new_status == "complete"` |

### `app/modules/payment_application/service.py`

| Location | Old | New |
|----------|-----|-----|
| `create_application()` INSERT | `'pending'` | `'open'` |
| `create_application()` gate check | `not in ("approved","paid")` | `not in ("on_process","complete")` |
| `update_actual_payment()` UPDATE | `status='completed'` | `status='complete'` |

### `app/modules/payment_application/routes.py`

| Location | Old | New |
|----------|-----|-----|
| `index()` memo filter | `status="approved"` | `status="on_process"` |

### `app/modules/beasiswa/service.py`

Three deletion guards that incorrectly checked for `"approved"` (a status that never existed in `payment_beasiswa`). Changed to `"complete"` to block deletion of finished payments.

| Line | Old | New |
|------|-----|-----|
| ~658 | `row["status"] == "approved"` | `row["status"] == "complete"` |
| ~722 | `row["status"] == "approved"` | `row["status"] == "complete"` |
| ~960 | `pay["status"] == "approved"` | `pay["status"] == "complete"` |

### `app/database.py`

Change `DEFAULT 'draft'` to `DEFAULT 'open'` for: `payment_beasiswa`, `payment_memo`, `pam_records`, `payment_application`.

### `app/modules/payment_memo/api.py`

| Location | Old | New |
|----------|-----|-----|
| Bulk action filter | `pb.status='draft'` | `pb.status='open'` |

### `app/modules/dashboard/routes.py`

| Location | Old | New |
|----------|-----|-----|
| `memo_draft` stat query | `status = 'draft'` | `status = 'open'` |

---

## Template Changes

Status badge strings/classes in:
- `app/templates/payment_memo/index.html`
- `app/templates/etf_payment_application/index.html`
- `app/templates/payment_application/index.html`
- `app/templates/beasiswa/index.html`

Update all badge labels: `draft → Open`, `in_memo → On Process`, `approved → On Process`, `paid → Complete`, `pending → Open`, `completed → Complete`.

---

## Test Updates

| File | Change |
|------|--------|
| `test_payment_memo_service.py` | `"in_memo"` → `"on_process"`, `"draft"` → `"open"` |
| `test_beasiswa_service.py` | `"draft"` → `"open"` |
| `test_pam_service.py` | `"draft"` → `"open"`, `"approved"` → `"on_process"`, `"paid"` → `"complete"` |
| `test_pam_pa_cascade.py` | INSERT fixtures `"draft"` → `"open"` |
| `test_payment_memo_ipay.py` | INSERT fixtures `"draft"` → `"open"` |

---

## Execution Order

1. Run `python app/migrate_status.py` (backup + migrate DB)
2. Apply all code changes (services, routes, templates, tests)
3. Run test suite: `python -m pytest app/tests/`
4. Spot-check UI for badge labels

---

## Additional Code Change: SML SLA status validation

`update_sml_status()` in `payment_memo/service.py` allows `{"open","approved","paid"}` for `sml_pa`. Since `sml_pa` is a student-based PA table (same schema as `etf_pa`), its status validation must also align:

```python
# payment_memo/service.py — update_sml_status()
_ALLOWED = {"open", "on_process", "complete"}
```

---

## Non-Goals

- `etf_pa`, `app_pa`, `sml_pa`, `setf_pa` — status values in DB already correct (open/on_process/complete), no DB migration needed
- `fiori_pa` — not defined in `database.py`; legacy vendor-tracking table, excluded from scope
- No UI redesign — only string value changes
