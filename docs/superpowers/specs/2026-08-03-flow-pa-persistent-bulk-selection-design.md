# FLOW Payment Application — Persistent Bulk Selection Design

## Problem

In Payment Application's data tabs (AGRI, APP, SML/LAND, SETF), the name filter (`f-nama`) calls `applyFiltersDebounced()` → `navigateWithFilters()`, which sets query params and does `window.location.href = ...` — a full page reload, since PA renders its table entirely server-side. Every reload wipes all DOM state, including checked `.row-chk` checkboxes.

Reported flow: search name 1 → check its row → search name 2 → name 1's checkmark is gone. Bulk actions (`bulkFillDate`/`bulkFillToday` via `doBulkUpdate`) only ever see whatever is currently checked in the DOM (`selectedPaIds()` reads `.row-chk:checked`), so there is no way today to build a selection across more than one search.

A chips UI (`renderPaChips()`, "● Tandai:" row) and a "✕ Batalkan Pilihan" clear button already exist in `bulk-bar`, but both currently just reflect/act on the DOM's checked state, not any persisted selection.

## Decisions (confirmed with user)

- **Scope:** selection persists per tab (AGRI/APP/SML/SETF each have their own independent selection). Switching tabs does not carry a selection over.
- **Duration:** `sessionStorage` — selection survives repeated searches/reloads within the same browser tab session, clears when the tab/browser closes or the user logs out. Not `localStorage`.
- **Reset filter button:** does NOT clear the selection — "Reset" only clears filter inputs. The existing "✕ Batalkan Pilihan" button remains the only way to explicitly clear the selection.

## Design

### Storage

A `sessionStorage` entry per tab: key `fh-pa-selected:<tab>` (e.g. `fh-pa-selected:agri`), value a JSON array of `{id, nama}` objects. Storing `nama` alongside `id` (not just `id`) lets chips display a selected row's name even when that row isn't part of the currently-rendered result set (e.g. after searching a different name).

New helpers in `app.js`, following the existing `_filterOpenKey`/`persistFilterOpen` sessionStorage pattern:
- `_paSelectionKey(tab)` → `'fh-pa-selected:' + tab`
- `getSelectedPa(tab)` → parsed array (empty array if missing/invalid JSON)
- `setSelectedPa(tab, list)` → serializes and stores
- `addSelectedPa(tab, id, nama)` → adds `{id, nama}` if not already present (dedup by id)
- `removeSelectedPa(tab, id)` → removes the entry with that id
- `clearSelectedPa(tab)` → removes the sessionStorage key entirely

### Checkbox interactions

- `onRowCheck()`: when a row's checkbox is checked, call `addSelectedPa(ACTIVE_TAB, id, nama)` (reading `nama` from the row's existing `data-nama` attribute); when unchecked, call `removeSelectedPa(ACTIVE_TAB, id)`.
- `toggleAll(chk)`: when checking "select all", add every *currently rendered* row's `{id, nama}` to the set (union — does not touch entries belonging to rows not currently rendered). When unchecking, remove only the currently rendered rows' ids from the set.
- On page load (after the server-rendered table is in the DOM), a new `restorePaSelection()` function reads `getSelectedPa(ACTIVE_TAB)` and, for each entry whose `id` matches a rendered row's checkbox value, checks that checkbox and adds the `row-sel` class to its `<tr>`. Then updates the "select all" header checkbox's checked state (checked only if every currently-rendered row is present in the set) and calls `updateBulkBar()`.

### Chips and bulk actions read from the persisted set, not the DOM

- `renderPaChips()` is changed to read `getSelectedPa(ACTIVE_TAB)` instead of `document.querySelectorAll(".row-chk:checked")`. This means chips reflect the full cross-search selection, including rows not currently rendered.
- `selectedPaIds()` (consumed by `doBulkUpdate`) is changed to read `getSelectedPa(ACTIVE_TAB).map(e => e.id)` instead of scanning the DOM. This is what makes bulk actions (`bulkFillDate`/`bulkFillToday`) apply to rows selected in an earlier search, not just what's currently visible.
- `removePaChip(paId)` calls `removeSelectedPa(ACTIVE_TAB, paId)` in addition to its existing DOM-uncheck behavior (for when the row happens to still be rendered).
- `updateBulkBar()`'s visibility/count (`bulk-bar` shown, "`${sel.length} baris dipilih`") is driven by the persisted set's length, not the DOM-checked count.

### Clear behavior

- `clearSelection()` (the "✕ Batalkan Pilihan" button) calls `clearSelectedPa(ACTIVE_TAB)` in addition to its existing DOM-uncheck behavior.
- `resetFilters()` is unchanged — it only touches filter query params, never the selection.

### Scope boundary

Each of the four data tabs (AGRI, APP, SML, SETF) uses its own `ACTIVE_TAB`-keyed sessionStorage entry, so selections never mix across tabs. The `input`/`summary`/`advance` tabs don't have this checkbox/bulk-action UI at all (per the existing `{% if active_tab not in ('input', 'summary', 'advance') %}` guard) and are unaffected.

## Out of scope

- Cross-tab selection (a single "cart" spanning AGRI+APP+etc.) — explicitly declined.
- Persisting selection beyond the browser tab's session (`localStorage`) — explicitly declined.
- Any change to the `bulk-update` API endpoint itself — it already accepts an arbitrary `pa_ids` array; this feature only changes how that array is assembled client-side.
- Any change to Payment Memo, Sponsorship, or any other module's selection/bulk mechanisms.
