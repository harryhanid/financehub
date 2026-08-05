# Budget Dashboard — Surface Missing Expired/Compliance Insights — Design

## Problem

`get_dashboard_data()` (`modules/budget/service.py:588-606`) computes two
analyses — `expiredAnalysis` (`analyze_expired_budgets`, lines 468-506) and
`complianceData` (`analyze_compliance`, lines 537-559) — and returns both in
the `/budget/api/dashboard-data` response. `budget.js`'s
`budgetLoadDashboard()` (lines 106-137) reads `data.summary`,
`data.notifications`, and 6 chart fields from that same response, but never
references `data.expiredAnalysis` or `data.complianceData` anywhere in the
file (confirmed — zero matches). `dashboard.html` (47 lines total) has no
corresponding section for either. The data has been computed and shipped to
the browser on every dashboard load, and silently discarded.

## Goal

Add two new sections to the Budget Dashboard displaying this already-computed
data, using the page's existing visual vocabulary (stat cards, plain
tables) rather than introducing new chart types — this is a "wire up what
already exists" fix, not a new feature build.

## Design

### Data shapes (already produced, unchanged by this work)

```python
# expiredAnalysis
{
  "totalExpired": int, "totalAmount": float, "totalRealized": float,
  "byDept": [{"dept": str, "count": int, "amount": float, "realized": float}],
  "byCompany": [{"company": "PO"|"TF", "count": int, "amount": float, "realized": float}],
  "ageBuckets": {"recent": int, "midterm": int, "longterm": int},  # ≤30d / 31-90d / >90d past deadline
}

# complianceData
{
  "totalExpired": int, "totalRequests": int,
  "approved": int, "pending": int, "rejected": int,
  "carryoverCount": int, "additionalCount": int,
  "additionalApproved": int, "additionalAmountApproved": float,
  "complianceRate": str,  # e.g. "83.3" — % of expired budgets covered by an approved carryover
}
```

### New section 1: "Analisis Budget Expired" (`dashboard.html`, after the existing `.budget-chart-grid`)

```html
<div class="budget-card">
  <h3>Analisis Budget Expired</h3>
  <div class="budget-summary-grid" id="budget-expired-summary"></div>
  <div class="budget-chart-grid" style="margin-top:.75rem">
    <div class="budget-chart-card">
      <h3>Per Department</h3>
      <table class="budget-table" id="budget-expired-dept-table"></table>
    </div>
    <div class="budget-chart-card">
      <h3>Per Company</h3>
      <table class="budget-table" id="budget-expired-company-table"></table>
    </div>
  </div>
</div>
```

`budgetRenderExpiredAnalysis(expiredAnalysis)` (new function in `budget.js`,
next to `budgetRenderSummary`) renders:
- Into `#budget-expired-summary`, 5 stat cards using the exact
  `.budget-stat-card` markup `budgetRenderSummary` already uses: Total
  Expired, Total Amount, Total Realized, and the 3 age buckets (labeled
  "≤30 Hari", "31-90 Hari", ">90 Hari").
- Into `#budget-expired-dept-table` / `#budget-expired-company-table`, a
  header row (Dept/Company, Jumlah, Amount, Realized) followed by one row
  per `byDept`/`byCompany` entry, amounts formatted via the existing global
  `fmtRupiah()` (from `app.js`, already loaded on every page) with a
  `"Rp "` prefix — matching how every other currency value in this app is
  displayed client-side.

### New section 2: "Compliance Carryover/Tambahan" (`dashboard.html`, after section 1)

```html
<div class="budget-card">
  <h3>Compliance Carryover/Tambahan</h3>
  <div class="budget-summary-grid" id="budget-compliance-summary"></div>
</div>
```

`budgetRenderCompliance(complianceData)` (new function in `budget.js`)
renders 7 stat cards into `#budget-compliance-summary`, same
`.budget-stat-card` markup: Compliance Rate (as `"<value>%"`), Total
Requests, Approved, Pending, Rejected, Carryover Count, Additional Count +
Additional Amount Approved shown as one combined card ("X disetujui — Rp Y").

### Wiring

In `budgetLoadDashboard()`'s existing `.then()` callback (`budget.js:110-133`),
add two calls alongside the existing render calls:

```javascript
budgetRenderExpiredAnalysis(data.expiredAnalysis);
budgetRenderCompliance(data.complianceData);
```

No backend change — `get_dashboard_data()` already returns both fields;
this is a frontend-only fix (2 new template sections + 2 new render
functions + 2 new call sites).

## Testing

- No frontend test framework exists in this codebase (consistent
  precedent) — verification is a route-level smoke test plus manual check.
- Route test: `GET /budget/` (dashboard page) returns 200 and contains the
  new section ids (`budget-expired-summary`, `budget-compliance-summary`).
- Route test: `GET /budget/api/dashboard-data` (already-existing endpoint,
  unchanged) still returns `expiredAnalysis`/`complianceData` keys —
  regression guard proving this fix didn't accidentally touch the backend.
- Manual: open Budget Dashboard with data that includes at least one
  Expired budget and at least one Carryover/Additional request in various
  statuses; confirm both new sections render real numbers (not "undefined"
  or blank), confirm the department/company table rows match what's
  visible in Kelola Budget for the same filtered data, confirm Compliance
  Rate matches `expired_covered / totalExpired * 100` by spot-checking one
  case by hand.

## Out of Scope

- Kelola Budget, Kelola Realisasi, Carryover/Tambahan tabs — explicitly
  deferred; this covers Dashboard only, per this session's confirmed scope.
- Any change to `analyze_expired_budgets`/`analyze_compliance`'s
  computation logic — both are already correct and tested implicitly by
  every other consumer; only their (previously nonexistent) presentation
  is added.
- Any new chart type — both sections use stat cards + plain tables,
  matching the page's existing style, not Chart.js.
