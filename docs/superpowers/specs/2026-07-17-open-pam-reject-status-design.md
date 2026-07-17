# Design: Reject Status for Open PAM (per-student and per-group)

**Date:** 2026-07-17
**Module:** Finance Hub — Payment Approval Memo (PAM) / Open PAM tab
**Status:** Approved

---

## Summary

The Open PAM tab currently has two destructive actions:

- **"Hapus"** on a per-student detail row (`removeStudentFromPAM` → `remove_student_from_pam`) — permanently `DELETE`s the `payment_beasiswa` row and reverts the linked PA (`etf_pa`/`app_pa`/`sml_pa`/`energy_pa`/`setf_pa`) back to `status='open'`.
- **"Cancel"** on a whole PAM group in the pillar tabs (`cancelPAM` → `cancel_pam_record`) — same idea, but deletes every `payment_beasiswa` row under that `pam_no` at once.

Both discard data and make the underlying PA available again for a new payment attempt. This adds a third option, **"Reject"**, at both granularities, that *preserves* the data with a new `status='rejected'` instead of deleting it, and marks the linked PA as `rejected` (terminal — not available for reuse), with an optional free-text reason.

---

## Decisions

| Question | Decision |
|---|---|
| Granularity | Both per-student (detail row) and per-group (PAM header) |
| Data retention | Preserved — `status='rejected'`, never deleted |
| Reason field | Optional, captured via `prompt()` (same lightweight pattern as `openRealizeModal`) |
| Visibility after reject | Shows in the normal pillar tab list (AGRI/APP/LAND/SETF/SMT/Advance) with a red "Rejected" badge, same as any other status |
| Reopen | Not supported in this iteration — reject is final via the UI |
| Linked PA status | Also becomes `rejected` (terminal) — not reverted to `open`, so it stops appearing in the "select PA to pay" picker |

---

## Architecture

### Data flow — per-student reject

```
User clicks "Reject" on a detail row
  └─► prompt() for optional reason
        └─► POST /payment-memo/pam/reject-student
              └─► reject_student_from_pam(payment_beasiswa_id, company_id, reason)
                    ├─ guard: parent pam_records.status must be 'open'
                    ├─ UPDATE payment_beasiswa SET status='rejected', reject_reason=?
                    ├─ recompute pam_records.total_amount from remaining non-rejected siblings
                    │     └─ if none remain → pam_records.status = 'rejected' too
                    └─ if the linked PA (via etf_pa_line_id) has no other active
                       payment anywhere → that PA row also becomes 'rejected'
```

### Data flow — per-group reject

```
User clicks "Reject" in #pam-memo-bar (checked groups)
  └─► prompt() for optional reason
        └─► POST /payment-memo/pam/reject
              └─► reject_pam_record(pam_id, company_id, reason)  [one call per checked group]
                    ├─ source == 'etf_agri': UPDATE etf_pa SET status='rejected' WHERE nomor_pam=?
                    │  UPDATE pam_records SET status='rejected', reject_reason=?
                    └─ source == 'beasiswa': UPDATE payment_beasiswa SET status='rejected',
                       reject_reason=? WHERE pam=? (all rows)
                       UPDATE pam_records SET status='rejected', reject_reason=?
                       for each distinct PA linked via those rows' etf_pa_line_id:
                         if no other active payment references it anywhere → PA status='rejected'
```

Both functions mirror the existing `remove_student_from_pam` / `cancel_pam_record` control flow exactly — same guards, same "is this PA still referenced elsewhere?" check — the only behavioral change is landing on `UPDATE ... status='rejected'` instead of `DELETE`.

`klaim_medical` rows are no longer deleted on reject (they were deleted alongside `payment_beasiswa` in the old delete flow) — since the parent row now survives, its medical-claim detail survives with it.

---

## Database Schema

### New column: `reject_reason TEXT` (nullable)

Added via the existing idempotent `ALTER TABLE ... ADD COLUMN` pattern in `database.py`'s `init_db()`, to:

- `payment_beasiswa`
- `pam_records`
- `etf_pa`, `app_pa`, `sml_pa`, `energy_pa`, `setf_pa`

### New status value: `'rejected'`

No schema change needed — `status` columns are plain `TEXT`, already storing `open` / `on_process` / `complete` / `partial`. `'rejected'` is just another value in that same column, on:

- `payment_beasiswa.status`
- `pam_records.status`
- `etf_pa.status` / `app_pa.status` / `sml_pa.status` / `energy_pa.status` / `setf_pa.status`

---

## Component Changes

### 1. `database.py`
- `init_db()`: add idempotent `ALTER TABLE <t> ADD COLUMN reject_reason TEXT` for the six tables listed above.

### 2. `modules/payment_memo/service.py`
- Add `reject_student_from_pam(payment_beasiswa_id, company_id, reason=None) -> dict`
- Add `reject_pam_record(pam_id, company_id, reason=None) -> dict`

### 3. `modules/payment_memo/routes.py`
- Add `POST /payment-memo/pam/reject-student` → `reject_student_from_pam`
- Add `POST /payment-memo/pam/reject` → `reject_pam_record`

### 4. `templates/payment_memo/index.html`
- Detail-row "Reject" button next to Edit/Hapus (mirrors `removeStudentFromPAM`'s wiring).
- `#pam-memo-bar`: new "Reject" button next to "Mark Complete", operating on `.pam-check:checked` groups (same selection the Mark Complete flow already reads).
- `_statusBadge()`: add a `rejected` entry (red/danger style).
- Status filter `<select>`s that currently list `open`/`on_process`/`complete`/`partial` (AGRI/APP/LAND/SETF/SMT/Advance ×2 = ~7 dropdowns): add `rejected` option.

### 5. `templates/etf_payment_application/index.html`
- Status filter dropdowns (4 occurrences) and the inline status-badge class logic (2 occurrences): add `rejected` handling (red/gray-danger badge).

### 6. Existing "does this PA still have an active payment" checks — must exclude rejected rows

Today, a PA's linked `payment_beasiswa` rows only ever disappear via hard `DELETE`, so every "is this PA still in use?" check is a plain `COUNT(*)` with no status filter — "exists" and "active" mean the same thing. Once rejected rows persist instead of being deleted, that's no longer true: a rejected sibling still physically exists in `payment_beasiswa`, so an unpatched `COUNT(*)` would count it as "still active" and incorrectly block the PA from reverting to `open` when the user later removes/deletes the last *actually* active payment referencing it.

Four existing call sites share this exact query shape and all need `AND pb.status != 'rejected'` added to their `WHERE`:
- `modules/beasiswa/service.py` (two occurrences, ~line 754 and ~line 823 — both inside the existing "revert PA to open" cascade of the draft-payment delete path)
- `modules/payment_memo/service.py` (two occurrences, ~line 1175 in `cancel_pam_record` and ~line 1269 in `remove_student_from_pam`)

This is a small, targeted fix to existing code made necessary by this feature — not a new feature itself — so it ships as its own commit before the new reject functions are added, per the plan's task breakdown.

### No change needed
- `get_draft_payments()` (Open PAM list query) already filters `WHERE status = 'open'` — rejected rows disappear from Open PAM automatically.
- `get_draft_siswa()` (the "pick a PA to pay" autocomplete in Input Payment) already filters `WHERE LOWER(p.status) = 'open'` — a rejected PA stops being selectable automatically.
- `get_pam_by_pillar()` (AGRI/APP/etc. pillar tab list) has no default status filter — rejected rows show up in the normal list automatically once the badge exists.

### Out of scope (flagged, not fixed here)

Several dashboard/report aggregations (`beasiswa/service.py` cat1 breakdowns, `bank/service.py` running totals) `SUM(amount)`/`COUNT(*)` over `payment_beasiswa` with no status filter at all — they already mix `open` and `complete` rows today. Once rejected rows persist, these would start folding rejected amounts into totals too. This pre-dates and is broader than this feature (it's a reporting-accuracy question, not something that breaks the reject flow itself), so it's called out here for awareness but left for a separate pass rather than bundled into this plan.

---

## Error Handling

- Same guard as the existing delete path: per-student reject is rejected with an error if the parent `pam_records.status != 'open'` (can't modify a PAM that's already on_process/complete).
- Reason is optional — `prompt()` returning `null` (user clicked Cancel) aborts the whole action client-side, no request sent. Returning `""` (empty string, OK clicked with nothing typed) proceeds with `reject_reason = NULL`.
- No new failure modes beyond what `remove_student_from_pam` / `cancel_pam_record` already handle (PAM not found, payment not found).

---

## Testing

- Unit: `reject_student_from_pam` — one row in a multi-row group → sibling rows untouched, PAM total recalculated excluding the rejected row, PAM stays `open`.
- Unit: `reject_student_from_pam` — last remaining active row in a group → PAM itself flips to `rejected`.
- Unit: `reject_student_from_pam` — linked PA with no other active payment → PA flips to `rejected` (not `open`).
- Unit: `reject_student_from_pam` — linked PA still has another active payment elsewhere → PA left untouched.
- Unit: `reject_pam_record` — beasiswa-source group with multiple students → all rows + PAM become `rejected`, reason stored.
- Unit: `reject_pam_record` — `etf_agri`-source PAM → `etf_pa.status` becomes `rejected` directly.
- Unit: guard rejects when parent PAM is not `status='open'`.
- Regression: confirm `get_draft_payments()` no longer returns rejected rows; `get_draft_siswa()` no longer returns a PA rejected via this flow.
- Regression: after one sibling in a group is rejected, deleting ("Hapus") the last remaining *active* sibling still correctly reverts the PA to `open` (proves the 4 patched "active payment" checks correctly exclude the rejected row instead of miscounting it as still-active).
