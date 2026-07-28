# Design: Vendors Tab in Payment Approval Memo

**Date:** 2026-07-28
**Module:** Finance Hub — Payment Approval Memo (`modules/payment_memo`)
**Status:** Approved

---

## Summary

The "Perusahaan" (company/vendor) field used throughout Payment Approval Memo's Input tab (and referenced across the AGRI/APP/LAND/SETF pillar tabs' data) is backed by the `vendors` table (`id`, `name`, `pillar`, `cost_center`). There is currently no UI to add or fix vendor records — the table was seeded once via a migration script and has been read-only ever since. When a needed company isn't in the list, there is no way to add it short of editing the database directly.

This adds a new "Vendors" tab inside the existing Payment Approval Memo module — not a separate page or module — where any logged-in user can view, search, add, and edit vendor records.

---

## Decisions

| Question | Decision |
|---|---|
| Where does this live? | A new tab inside Payment Approval Memo (`tab-vendors`), alongside Open PAM/Input/AGRI/APP/LAND/SETF — not a separate module, not a separate top-level nav entry. |
| Access control | Open to all logged-in users, same as the rest of Payment Memo — no admin gate. |
| Which fields? | Only the 3 that already exist on the table: `name`, `pillar`, `cost_center`. No schema changes, no new columns. |
| Pillar input | A fixed dropdown (AGRI / APP / LAND / SETF) — not free text. This directly prevents the class of bug just fixed (a mistyped or inconsistently-cased pillar value silently breaking downstream pillar-filtered views). Legacy values already present on old rows (`NON PILLAR`, `NON ALLOCATED`, `-`) are not offered as options for new/edited vendors — those stay as historical data on existing rows, not reproducible through this form. |
| Name uniqueness | Enforced (matches the existing `UNIQUE NOT NULL` DB constraint) — attempting to add or rename to a name that already exists shows a clear inline error, not a crash. |
| Cost center | Free text, optional, no format validation — matches the existing SAP-style codes already in the data (e.g. `5101C1POFF`). |
| Edit support | Yes — list + inline edit per row, not add-only. Lets a typo (e.g. wrong cost center) be corrected without direct DB access. |
| Search | Yes — a search box filtering by name, using the same `.filter-bar.collapsible` convention as the other Payment Memo tabs (so it inherits the `F`-key/auto-focus behavior already built for those tabs, at no extra cost). |
| Relationship to `get_vendors()` | Untouched. `beasiswa/service.py`'s `get_vendors(search)` (used by the Input tab's vendor autocomplete) keeps working exactly as today. The new tab uses its own read function (`list_vendors()`) in `payment_memo/service.py`, because it needs `id` (for edit) which `get_vendors()` doesn't return, and because keeping this tab's code inside the module that owns it is more consistent than reaching into Beasiswa's service module for something Payment Memo now owns the UI for. |

---

## Architecture

### File changes

**Modify `C:\Financehub\app\modules\payment_memo\service.py`** — add three functions:
- `list_vendors(search: str = "") -> list` — `SELECT id, name, pillar, cost_center FROM vendors [WHERE name LIKE ?] ORDER BY name`.
- `add_vendor(name: str, pillar: str, cost_center: str) -> dict` — validates `name`/`pillar` are non-empty, inserts, catches `sqlite3.IntegrityError` for the uniqueness constraint and returns `{"ok": False, "pesan": "Nama vendor sudah terdaftar."}` instead of raising.
- `update_vendor(vendor_id: int, name: str, pillar: str, cost_center: str) -> dict` — same validation/uniqueness handling, `UPDATE vendors SET ... WHERE id = ?`.

**Modify `C:\Financehub\app\modules\payment_memo\routes.py`** — add three routes, following this module's existing `@jwt_html_required`-only pattern (no admin gate, matching every other route in this file):
- `GET /vendors` (JSON, called by the tab's `loadVendors()`) — returns `list_vendors(search)` filtered by a `?search=` query param.
- `POST /vendors/add` — reads `name`/`pillar`/`cost_center` from JSON body, calls `add_vendor`.
- `POST /vendors/<int:vendor_id>/edit` — same fields, calls `update_vendor`.

**Modify `C:\Financehub\app\templates\payment_memo\index.html`**:
- Add `<button class="tab-btn" data-tab="tab-vendors" onclick="loadVendors()">Vendors</button>` to the existing `.tabs` bar.
- Add a new `<div class="tab-panel" id="tab-vendors">` containing: a `.filter-bar.collapsible` with a name search input (first field, matching the auto-focus convention) and a pillar filter dropdown (`<option value="">Semua Pillar</option>` + AGRI/APP/LAND/SETF); a table listing all vendors (columns: Nama, Pillar, Cost Center, Aksi); an inline "add vendor" form above the table (name text input, pillar `<select>` with exactly `<option value="AGRI">AGRI</option><option value="APP">APP</option><option value="LAND">LAND</option><option value="SETF">SETF</option>` — no blank/placeholder option, no legacy values, cost center text input, submit button) — inline rather than a modal, matching this page's existing preference (the Input tab itself is inline, not modal-based).
- Add `loadVendors()`, `addVendor()`, and an edit-in-place handler (click a row → fields become editable inputs → save/cancel), following the same JS conventions already used by `loadFIORI()`/`loadSETF()`/etc. in this file (skeleton loading rows, `esc()` for XSS-safe rendering, `showToast()` for success/error feedback).

### Non-goals

- No changes to the `vendors` table schema.
- No changes to `get_vendors()` or the Input tab's vendor autocomplete — both keep working exactly as today.
- No delete/deactivate capability — out of scope; a vendor already referenced by historical PAM records shouldn't disappear from those records' display, and soft-delete/deactivate is a separate design question not needed to solve today's problem (adding missing vendors).
- No bulk import — one vendor at a time, matching the scale of the actual need (occasional missing entries, not a data migration).
- No retroactive fix for historical rows already tagged `NON PILLAR`/`NON ALLOCATED`/`-` — those are untouched.

---

## Testing

**Backend (pytest, matching this module's existing test conventions):**
- `list_vendors()` — returns all vendors; returns filtered subset when `search` is passed.
- `add_vendor()` — succeeds with valid data; returns `ok: False` (not an exception) when `name` already exists; returns `ok: False` when `name` or `pillar` is empty.
- `update_vendor()` — succeeds; returns `ok: False` when renaming to a name already used by a *different* vendor; succeeds when "renaming" to its own current name (no-op case).
- Route-level: `GET /payment-memo/vendors`, `POST /payment-memo/vendors/add`, `POST /payment-memo/vendors/<id>/edit` — happy path and duplicate-name path for each POST.

**Frontend (manual, no JS test framework in this codebase — same approach used throughout this module):**
- Add a vendor, confirm it appears in the list without a page reload.
- Edit a vendor's cost center, confirm the change persists after reload.
- Attempt a duplicate name (both on add and on edit), confirm a clear toast error and no partial/corrupt state.
- Confirm the search box filters the list, and confirm `F` auto-focuses it (inherited from the existing shared `toggleFilterPanel()` fix — no new code needed for this, just confirms the inheritance works for a newly-added tab).
- Confirm a vendor added here immediately appears in the Input tab's "Perusahaan" autocomplete (proves `list_vendors()`/`get_vendors()` reading the same table stay in sync without any explicit wiring between them).

## Out of Scope

- Additional vendor fields (NPWP, address, bank account, contact person) — explicitly deferred; only the 3 existing columns are used.
- Admin-only access restriction — explicitly rejected; open to all logged-in users.
- A standalone "Vendors" module/page with its own nav entry — explicitly rejected in favor of a tab inside Payment Memo.
