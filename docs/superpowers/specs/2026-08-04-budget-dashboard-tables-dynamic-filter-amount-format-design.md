# Budget Dashboard — Group Tables, Dynamic Filter, Amount Format

## Problem

On Sinar Mas Tjipta → Budget → Dashboard, three requests:

1. The "Per Department", "Per Activity", "Per Category" charts are hard to
   scan for the biggest items — a sorted table would read better.
2. Changing a filter select requires an extra "Terapkan Filter" click
   before the dashboard updates.
3. Every money amount on the page shows the full Rupiah value with a
   "Rp" prefix (and some Chart.js tooltips would show a "Jt" suffix if a
   millions-scaled formatter were introduced) — should be a plain number
   rounded to millions, no prefix or suffix, matching the fix already
   shipped for the Sponsorship Dashboard.

## Scope

Route: `GET /budget/` (`app/templates/budget/dashboard.html`,
`app/static/js/budget.js`). No backend (`app/modules/budget/service.py`,
`app/modules/budget/routes.py`) or API response shape changes — every
raw number this page needs is already present in the existing
`/budget/api/dashboard-data` response alongside today's pre-formatted
strings; this is a presentation-only change.

## Design

### 1. Per Department / Activity / Category → tables

Replace the three `<canvas>` bar charts (`chart-dept`, `chart-activity`,
`chart-category`) with `<table class="budget-table">` elements, styled
identically to the existing "Analisis Budget Expired" breakdown tables
already on this same page. Columns: **Nama** (department/activity/
category label), **Jumlah Item**, **Budget**, **Realisasi** — rows in
the order the API already returns them (`group_budget_vs_realized()`
already sorts by budget descending server-side; no backend change).

The other three charts — "Budget vs Realisasi per Bulan" (bar),
"PO vs TF" (donut), "Status" (donut) — are untouched, still charts.

### 2. Dynamic filter

Remove the "Terapkan Filter" button (`#bf-apply`). Each of the five
filter `<select>` elements (`#bf-company`, `#bf-dept`, `#bf-year`,
`#bf-category`, `#bf-activity`) gets a `change` listener that calls
`budgetLoadDashboard()` directly — same function the button already
calls today, just triggered per-select instead of once via a button.

### 3. Amount format — plain number, rounded to millions

Every money amount on this page (summary cards, expired-analysis cards
and its two breakdown tables, compliance cards, and the three new
group tables from §1) drops its "Rp" prefix and is rounded to whole
millions with no suffix — e.g. today's "Rp 607.473.125" becomes "607".
Chart.js tooltips on the three charts that remain charts (§1) use the
same formatting for their values.

This reuses the exact rounding/locale-formatting logic already shipped
for the Sponsorship Dashboard fix (`Math.round(n / 1000000)` +
`toLocaleString("id-ID")`, no prefix, no suffix) — a shared helper
function, not a copy-pasted one, since this is now the second dashboard
using it.

## Out of Scope

- Any other Budget tab (Kelola Budget / Kelola Realisasi / Carryover) —
  not part of this request, keep showing full "Rp ..." amounts as today.
- Any backend/API change — all data needed is already returned.
- The three charts that stay charts (Bulanan, PO vs TF, Status) changing
  chart type — only their tooltip number formatting changes.
