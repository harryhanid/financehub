# Design: Beasiswa Dashboard Grid Gap Fix & Latest-Transactions Status Badge

**Date:** 2026-08-03
**Module:** Finance Hub — Sub Modul Beasiswa / Dashboard tab
**Status:** Approved
**Amends:** [2026-08-03-beasiswa-dashboard-card-reorder-design.md](2026-08-03-beasiswa-dashboard-card-reorder-design.md) — adds a CSS fix that design's markup change exposed; the section-panel/card-order structure it defined is otherwise unchanged.

---

## Summary

The user manually implemented the card-reorder design (splitting each Grafik panel's mixed grid into a chart-row and a table-row) and found two problems while reviewing the result:

1. **Empty grid cells.** `.beasiswa-dash-grafik-grid` is a fixed 2-column grid (`grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)`, `beasiswa_dashboard.css:27`), not auto-fit. Any grid holding an odd number of cards leaves its last row's second column blank. This affected "Perbandingan Realisasi per Bulan per Tahun" (a pre-existing gap — that card was already alone in a row before the reorder) and "Realisasi per Kategori" (chart) — a new gap, introduced by the reorder's chart/table split, since that chart went from sharing a 4-card grid (even) to being the sole occupant of its own chart-row.
2. **"20 Transaksi Terakhir" only shows completed payments.** `get_dashboard_latest_payments()` filters `WHERE p.status = 'complete'` (`service.py:1400`), so a payment the user just entered (status `open` by default until marked complete) never appears there, which reads as "the latest input isn't showing up." Confirmed with the user: this is the actual cause, not a query/caching bug.

## Decisions

| Question | Decision |
|---|---|
| Fix for empty grid cells | Add one CSS rule targeting "the odd-positioned last child" of `.beasiswa-dash-grafik-grid`, making a lone trailing card span both columns — fixes every current and future occurrence of this shape generically, no markup changes, no per-card exceptions to track |
| Alternative considered (revert to auto-fit) | Rejected — the 2-column fixed grid was a deliberate choice in the prior Filter Fix & Section Panels design specifically to avoid auto-fit "flowing all cards into 3-4 columns on a wide viewport"; the CSS rule above gets gap-free layout without giving that up |
| "20 Transaksi Terakhir" scope | Show all statuses (`open`, `complete`, `rejected`, whatever exists), not just `complete` — add a status badge per row so the distinction stays visible instead of silently hiding non-complete rows |
| Badge styling | Reuse the exact existing inline badge markup/colors from the Data Payment tab's `BADGE` map (`templates/beasiswa/index.html:1471-1475`: `open` = amber, `complete` = blue) for visual consistency within the same module. Statuses with no explicit mapping (e.g. `rejected`, which exists in production data at 1 row) fall back to plain text, matching that same existing table's fallback behavior (`BADGE[r.status] || r.status`) — not a new "rejected" design |
| Badge column position | End of the row (after "Realisasi"), matching the Data Payment tab's own column ordering (status column is near the end there too) |

---

## Architecture

### File changes

- **Modify:** `app/static/css/beasiswa_dashboard.css` — add one rule to the existing `.beasiswa-dash-grafik-grid` block.
- **Modify:** `app/modules/beasiswa/service.py` — `get_dashboard_latest_payments()` (currently `service.py:1382-1408`): drop the `AND p.status = 'complete'` clause, add `p.status` to the `SELECT`.
- **Modify:** `app/templates/beasiswa/index.html` — `dash-latest-payments-table`'s `<thead>` (5 columns today: Tanggal, Nama, Kategori, Kategori 2, Realisasi) gains a 6th `<th>Status</th>`; the "no data" fallback row's `colspan` goes from `5` to `6`.
- **Modify:** `app/static/js/dashboard_beasiswa.js` — `dashRenderLatestPaymentsTable()` (currently `dashboard_beasiswa.js:365-380`): render a new status-badge cell per row using a new small helper function; the `dashApplyFilters()` skeleton-row call for this table (`skeletonRows(5, 5)` at `dashboard_beasiswa.js:406`) updates its column count to `6`.

No backend route changes (`/beasiswa/api/dashboard/latest_payments` passes the service result straight through, already unaffected by the added `status` field). No changes to any other card, chart, or table.

### CSS fix

Add directly below the existing rule in `beasiswa_dashboard.css`:

```css
.beasiswa-dash-grafik-grid > *:nth-child(odd):last-child {
  grid-column: 1 / -1;
}
```

`:nth-child(odd):last-child` matches an element that is both in an odd position (1st, 3rd, 5th, ...) and the final child — i.e. exactly the "leftover" card that would otherwise pair with nothing. `grid-column: 1 / -1` makes it span every column instead of just one. A grid with an even card count is unaffected (its last child is even-positioned, so this selector never matches).

### Latest-payments query

```sql
SELECT p.tanggal, s.nama, p.cat1, p.cat2, p.amount, p.status
FROM payment_beasiswa p
JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
WHERE p.company_id = ?{payment_year_sql}{pillar_sql}{program_sql}{jenjang_sql}
ORDER BY p.tanggal DESC, p.id DESC
LIMIT ?
```

(Only the `AND p.status = 'complete'` clause is removed and `p.status` added to the column list — every filter/sort/limit clause is unchanged.)

### Status badge helper (JS)

New function in `dashboard_beasiswa.js`, mirroring the existing `dashCatBadge` helper's shape and reusing the Data Payment tab's exact badge markup:

```javascript
const DASH_PAYMENT_STATUS_BADGE = {
  open:     '<span style="background:#fef3c7;color:#d97706;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">Open</span>',
  complete: '<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600">Complete</span>',
};
function dashPaymentStatusBadge(status) {
  return DASH_PAYMENT_STATUS_BADGE[status] || status || "";
}
```

`dashRenderLatestPaymentsTable()` appends one more `<td>` per row calling this helper, and the fallback "Belum ada transaksi." row's `colspan` becomes `6`.

---

## Testing

Same no-frontend-framework verification pattern as the reorder design this amends:

- App-boot sanity check.
- CSS brace-balance check on `beasiswa_dashboard.css` after the edit.
- Force-render `/beasiswa/` via Flask test client with a real test-DB login — 200 OK, confirm the new CSS rule text and the new `<th>Status</th>` are present in the response.
- A service-level check (real SQLite fixture, not a live/production DB) confirming `get_dashboard_latest_payments()` now returns rows with `status: 'open'` when an uncompleted payment exists in range, and that the returned dicts include a `status` key.
- Manual browser check if a preview session with non-production data is available: confirm no visibly empty grid cell remains anywhere in the Grafik section, and that an `open`-status payment now appears in "20 Transaksi Terakhir" with an amber "Open" badge.
- Full Python regression suite run once at the end — no other backend logic changes in this task, so no new failures expected beyond whatever pre-existing/unrelated failures are already known.

## Out of Scope

- Any other card's data or chart logic — this touches only the grid CSS (global fix, all cards) and the one latest-payments query/table.
- Adding a badge style specifically for `rejected` or any other status beyond `open`/`complete` — falls back to plain text, matching the existing Data Payment tab's own behavior for the same case.
- The card reorder/regrouping itself (already specified separately) — this document only adds the CSS gap fix on top of it.
