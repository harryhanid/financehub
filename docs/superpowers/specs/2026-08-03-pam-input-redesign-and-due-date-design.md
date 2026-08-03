# Payment Approval Memo — Input Form Redesign & Due Date Fix — Design

## Problem

The PAM "Input" tab (`templates/payment_memo/index.html`, `#tab-input-payment`)
has two separate issues:

**1. Due date is inconsistent across three different places:**

| Where | Formula | Scope |
|---|---|---|
| Stored in `pam_records.due_date` (set at PAM creation, `service.py`) | `pam_date + 1 calendar month` (`_add_one_month`) | All 6 insert call sites (lines 627, 671, 751, 844, 925, 2441) |
| Shown in the printed PAM memo (`exports.py`, "Expected Due Date") | `pam_date + 8 workdays`, skipping weekends **and** `_HOLIDAYS_2026` (`_workday`) | Every print path |
| Previewed in the Input form itself (`_calcSmtDueDate()`, `index.html:5473-5485`) | `pam_date + 8 workdays`, skipping **only** weekends (no holiday check) | SMT GL/Advance lines only — not shown at all for AGRI/APP/LAND/SETF |

Three different values can exist for the same PAM depending on where you
look, and the field is only ever visible at print time for ETF pillars —
never in the form where the PAM is actually created.

**2. The Input form's visual treatment predates the color-coded-section
pattern already approved and shipped for the ETF Payment Application Input
form** (`2026-07-31-financehub-etf-pa-input-redesign-design.md`) — its field
groups have no visual grouping at all.

## Decisions (confirmed with user)

| Question | Decision |
|---|---|
| Which due-date formula is correct | `pam_date + 8 workdays`, skipping weekends and `_HOLIDAYS_2026` — i.e. the formula already used at print time (`_workday`). The stored `_add_one_month` value is the one that's wrong and gets replaced |
| Existing PAM records | Migrate — recompute and update `due_date` for every existing `pam_records` row to the new formula, not just new PAMs going forward |
| Due date field in the Input form | Read-only, auto-calculated from "Tanggal" — no manual override |
| Visual redesign direction | Reuse the exact color-coded `.form-section.tint-*` pattern from the ETF PA Input redesign (same tokens: `--accent`/blue, `--violet`, `--tangerine`) — **the existing field arrangement/order is kept as-is**, this only adds section framing + the one new field |

## Design

### 1. Consolidate `_workday`/`_HOLIDAYS_2026` into `service.py`

`_workday()` and `_HOLIDAYS_2026` currently live only in `exports.py`
(`exports.py:23-49`), which is the wrong direction for a dependency — the
PAM-creation insert functions in `service.py` need this logic too, and
`service.py` is the lower-level module. Both are moved into `service.py`
(near the existing `_add_one_month`, `service.py:238-246`); `exports.py`
then imports `_workday` from `service.py` instead of defining its own copy.
This becomes the single source of truth — the exact bug being fixed
(three independent implementations of "add N workdays") can't recur once
there's only one implementation.

`_add_one_month` itself is **not deleted** — grep confirms it has no other
callers once its 6 `due_date` call sites are switched to `_workday`, but
removing a helper function is a separate, easy follow-up; leaving it
unused-but-present is lower risk for this change and can be cleaned up
later if confirmed truly dead.

### 2. Fix all 6 due-date call sites in `service.py`

Every `due_date = _add_one_month(<date var>)` becomes
`due_date = _workday(<same date var>, 8)` — no other change to those
functions; the date variable already in scope (`tanggal` or `pam_date`,
depending on the function) is exactly what's stored as `pam_date` in the
same INSERT, matching what `exports.py` already reads (`pam.get("pam_date", "")`)
at print time.

### 3. New API endpoint for the Input form's live preview

`GET /payment-memo/api/due-date?tanggal=YYYY-MM-DD` → `{"due_date": "YYYY-MM-DD"}` (or a 400 with an error message for a missing/invalid `tanggal`). Calls
`_workday(tanggal, 8)` directly — the same function used at creation and
print time, so the Input form's preview can never drift from either again.

### 4. Input form: new Due Date field, all pillars

Row 1 of the shared header (`index.html:185-242`) gets one more field, placed
immediately after "Tanggal":

```html
<div class="form-group" style="margin:0">
  <label>Due Date</label>
  <input type="text" id="ipay-due-date" readonly placeholder="—"
         style="background:#f3f4f6;cursor:default;color:#374151;font-weight:600">
</div>
```

The grid's `grid-template-columns` (both the SMT and non-SMT variants) gains
one more track for this field. "Tanggal"'s `onchange` handler is changed
from calling `_calcSmtDueDate()` to fetching the new API endpoint and
filling `#ipay-due-date` with the result — this now runs for every
transaction type/pillar, not just SMT.

`_calcSmtDueDate()`, the `.smt-due-cell` class, and the `querySelectorAll('.smt-due-cell')`
call in the "Tanggal" input's `onchange` (`index.html:219`) are all removed
— superseded by the shared field above. (`.smt-due-cell` appears to only be
used to populate a due-date column within the SMT-lines table itself,
`index.html:5584-5586` — that in-table column is replaced by reading the
same shared `#ipay-due-date` value rather than recomputing per-row, since
due date doesn't vary per line item within one PAM.)

### 5. Visual redesign — color-coded sections, layout unchanged

Reusing the exact tokens/classes from the ETF PA Input redesign (already in
`style.css`: `--accent`/`--accent-surface`/`--accent-border`,
`--violet`/`-surface`/`-border`, `--tangerine`/`-surface`/`-border`, and the
`.form-section`/`.form-section-title`/`.form-section.tint-*` classes) — no
new tokens needed, since PAM's 3 sections map directly onto that palette:

| Section | Current markup | Tint |
|---|---|---|
| Identitas PAM (Row 1: Tipe/Transaksi, Tanggal, **Due Date**, No. PAM, Perusahaan) | `index.html:185-242` | `tint-jenis` (blue/`--accent`) |
| Metadata Auto (Row 2: Pillar, CC, Catatan Payment) | `index.html:243-259` | `tint-route` (violet) |
| Detail Transaksi (whichever of the 4 panels — Beasiswa/Klaim/Others/SMT-Lines — is currently active) | `index.html:260-433` | `tint-pay` (tangerine) |

Each of the two header `<div style="display:grid;...">` wrappers becomes
`<div class="form-section tint-jenis" style="display:grid;...">` /
`tint-route` respectively (existing inline grid styles stay — only a class
is added, no layout properties change). Each of the 4 panel `<div>`s
(`#ipay-panel-beasiswa`, `#ipay-panel-klaim`, `#ipay-panel-others`,
`#ipay-panel-smt-lines`) gets `class="form-section tint-pay"` added — since
exactly one is visible at a time (the others are `display:none`), only one
tinted box is ever seen, matching the "Daftar Pembayaran" treatment in the
PA Input redesign. Field order, table columns, and every existing style
attribute inside these sections are untouched — this is framing only.

### 6. Migration script for existing PAM records

`scripts/migrate_pam_due_dates.py` (new, one-off, run manually — matching
this repo's existing precedent for one-off data-fix scripts, e.g.
`migrate_status.py`, `fix_etf_pa_line_id_fk.py`):

1. Back up `finance_hub.db` first (timestamped copy, matching the existing
   `finance_hub_backup_before_*.db` naming convention already used
   throughout this repo's history).
2. `SELECT id, pam_date, due_date FROM pam_records`.
3. For each row, compute `new_due_date = _workday(pam_date, 8)`.
4. `UPDATE pam_records SET due_date = ? WHERE id = ?` only for rows where
   `new_due_date != due_date` (skip no-op writes).
5. Print a summary: rows updated vs. rows already correct.

## Testing

- Unit tests for `_workday`/`_HOLIDAYS_2026` in their new home (`service.py`)
  — none exist today (confirmed: no test file references `_workday` or
  `_HOLIDAYS_2026` anywhere). Cover: a plain weekday-only span, a span that
  crosses a weekend, and a span that crosses one of the 2026 holidays (e.g.
  starting right before Idul Fitri, `2026-03-19`–`2026-03-22`).
- For each of the 6 `service.py` insert functions touched: a test asserting
  the created `pam_records` row's `due_date` matches `_workday(pam_date, 8)`,
  not the old `+1 month` value.
- Route test for the new `/payment-memo/api/due-date` endpoint: valid date,
  a date landing exactly on/around a holiday, and an invalid/missing
  `tanggal` parameter.
- Test for `migrate_pam_due_dates.py`: seed rows with the old-formula
  `due_date`, run the script, assert every row now holds the new-formula
  value and the backup file was created.
- Manual: open the Input tab for each pillar (AGRI/APP/LAND/SETF) and for
  SMT, change "Tanggal", confirm "Due Date" populates and matches what the
  same PAM later shows when printed. Confirm the 3 sections render with
  their assigned tints and the field layout/order is otherwise identical to
  before.

## Out of Scope

- Deleting `_add_one_month` — left in place, unused, as a smaller separate
  cleanup.
- Making the Due Date field editable — explicitly decided against.
- Any change to the print memo's own due-date display logic beyond
  importing `_workday` from its new location — its output value is
  unchanged (same formula it already used).
- Any change to the 4 transaction panels' own internal fields, table
  columns, or save logic — only their outer wrapper gains a tint class.
- Removing the per-line due-date column inside the SMT-lines table
  entirely — it's repointed to the shared field's value, not deleted,
  unless during implementation it's confirmed genuinely redundant to keep
  a per-row copy at all.
