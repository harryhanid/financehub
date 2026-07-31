# FLOW Dynamic Pagination Page Size — Design Spec

## Problem

Paginated tables use a fixed page size regardless of screen height. On tall/maximized screens this leaves visible empty space below a partially-filled last page instead of showing more rows — the opposite of the full-bleed goal (full-bleed table pages spec/plan, 2026-07-31, separate effort). Reported via screenshot of Payment Memo's AGRI tab: "Menampilkan 1-50 dari 80 baris (halaman 1/2)" with empty space below the table.

## Current State (verified in code)

Three distinct pagination mechanisms exist across FLOW, each needing a different fix:

### 1. Payment Memo — client-side (`app/templates/payment_memo/index.html`)
- Only two tabs paginate: **SMT** (`_smtPageSize = 50`, line 2413) and **AGRI** (`_agriPageSize = 50`, line 3229). The other five pillar tabs (FIORI/APP, SML/LAND, SETF, Advance, Vendors) render all rows with no page-size limit — out of scope for this feature.
- All rows for the active tab are already loaded into memory (`_smtAllRows`, `_agriAllRows`) after one fetch.
- Page slicing, "Menampilkan X-Y dari Z baris (halaman N/M)" text, and prev/next state are all computed client-side in JS (e.g. lines 2469-2522 for SMT, mirrored at 3288+ for AGRI) — no server round-trip to change page size.

### 2. Payment Application — server-side, in-memory slice (`app/modules/etf_payment_application/routes.py`)
- `PA_PAGE_SIZE = 50` (line 40). Single route serves all tabs via `?tab=` query param.
- All matching rows are fetched and filtered in Python first (`filtered_rows`), then sliced by offset for the current page (lines 94-102): `total_pages = max(1, -(-total_rows // PA_PAGE_SIZE))`, `pa_rows = filtered_rows[offset:offset + PA_PAGE_SIZE]`.
- Page size is baked into the query string (`?page=N`) and a fresh request re-slices server-side — changing page size requires a new request.

### 3. Sponsorship — server-side, real SQL LIMIT/OFFSET (`app/modules/sponsorship/routes.py`)
- `PER_PAGE = 100` (line 18). Only the **Data** tab paginates (`sponsorship/data.html`, lines 172-175): `list_transaksi(_cid(), filters, limit=PER_PAGE, offset=(page-1)*PER_PAGE)`.
- Outstanding and Report tabs render all rows with no pagination — out of scope.
- Rows for pages beyond the first are never fetched from the DB until requested, unlike Payment Application which already has all rows in memory server-side.

## Design

### Page-size calculation (shared logic, all three modules)

On page load (after the table renders), JS measures:
- Available vertical space = viewport height minus navbar, module-tab row, filter bar (if open), page header, and pagination-bar heights (all already-rendered elements — use `getBoundingClientRect()`).
- Actual rendered row height = height of one `<tr>` in the just-rendered table body.
- `computedPageSize = floor(availableSpace / rowHeight)`, clamped to `[currentDefault, currentDefault * 4]` (min = today's default so we never show fewer rows than today; max cap prevents pathological values on extreme screen heights or if row height measures near-zero).

No recompute on window resize (confirmed by user) — only on page load/reload.

### Payment Memo (client-side): no reload needed

Rows are already in memory. After first render of a paginating tab:
1. Measure and compute `computedPageSize` as above.
2. If it differs from the hardcoded `_smtPageSize`/`_agriPageSize`, re-slice and re-render immediately from `_smtAllRows`/`_agriAllRows` using the new size — pure client-side, no network request.
3. Cache the computed size in `localStorage` (key `fh-pagesize:smt`, `fh-pagesize:agri`) alongside the viewport height it was computed for, so the next page load uses the cached value as the initial page size directly (skipping the one-frame flash of the default 50, then a re-render). If viewport height differs from the cached one by more than a small threshold, recompute instead of trusting the stale cache.

### Payment Application & Sponsorship (server-side): one calibration reload, then cache

Because the page size determines what the server sends, the first load must use *some* size before JS can measure anything. Flow:
1. Page loads with the existing default (`PA_PAGE_SIZE=50` or `PER_PAGE=100`), UNLESS a cached value exists in `localStorage` (key `fh-pagesize:pa`, `fh-pagesize:sponsorship-data`) for a matching viewport height — in that case, pass the cached size as a `page_size` query param on the initial request so no recalibration reload is needed.
2. After render, JS measures and computes `computedPageSize` as above.
3. If no cache was used and `computedPageSize` differs meaningfully from the size just rendered, trigger exactly ONE additional reload with `?page_size=<computedPageSize>` appended (preserving all existing filters/page params), and cache the result (size + viewport height) in `localStorage`.
4. Routes accept an optional `page_size` query param, falling back to `PA_PAGE_SIZE`/`PER_PAGE` when absent or invalid (e.g. non-numeric, ≤0, or above the clamp ceiling) — the constants become defaults, not the only possible value.

This means a first-ever visit costs one extra reload; every subsequent visit (same viewport height) loads correctly-sized in one request.

### Cache invalidation

`localStorage` entries store `{ pageSize, viewportHeight }`. On load, if the stored `viewportHeight` doesn't match the current one (within a small tolerance, e.g. ±20px, to absorb scrollbar/zoom noise), treat the cache as stale and recompute (client-side: immediate re-slice; server-side: one recalibration reload).

## Out of scope

- Payment Memo's non-paginating tabs (FIORI/APP, SML/LAND, SETF, Advance, Vendors) — they show all rows already, no page-size concept applies.
- Sponsorship's Outstanding and Report tabs — no pagination exists there today.
- Live recompute on window resize (explicitly declined by user) — only on page load/reload.
- Any change to filter logic, row content, or column layout.

## Open coordination note

Uncommitted working-tree changes were found in `sponsorship/data.html`, `outstanding.html`, `report.html`, and `bank/index.html` (not made by this session) that already include `{% set full_bleed = true %}` plus unrelated feature work (new filter dropdowns, export buttons, column reorder). This pagination feature touches the same Sponsorship Data tab template and its pagination-info markup — implementation should account for those pending uncommitted changes rather than assuming the file matches its last commit.
