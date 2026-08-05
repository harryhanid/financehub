# Budget Dashboard — Group Tables, Dynamic Filter, Amount Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On Budget Dashboard: turn the Per Department/Activity/Category charts into sorted tables, make the 5 filters apply on change (no button), and format every money amount on the page as a plain number rounded to millions — per `docs/superpowers/specs/2026-08-04-budget-dashboard-tables-dynamic-filter-amount-format-design.md`.

**Architecture:** A new shared JS formatter (`fmtJutaanBulat`, in `app.js` alongside the existing `fmtRupiah`/`fmtJutaan`) replaces every `"Rp " + fmtRupiah(...)` / backend-`formatted`-string usage on this page, and also becomes what the already-shipped Sponsorship Dashboard formatter delegates to (DRY, per the spec). The three group charts are replaced by a new table-rendering function fed by the exact same already-sorted API data the charts used. The filter button is removed in favor of `change` listeners on each select. `chart-status` shows counts, not money, so the pie-chart renderer takes an optional formatter parameter rather than always applying the millions formatter. No backend/API changes anywhere in this plan.

**Tech Stack:** Vanilla JS, Chart.js (already a dependency). No new dependencies.

## Global Constraints

- No backend/API changes — `app/modules/budget/service.py`, `app/modules/budget/routes.py` are untouched. Every value used was already present in the existing `/budget/api/dashboard-data` response.
- Only Budget Dashboard (`/budget/`) is affected — no other Budget tab (Kelola Budget/Realisasi/Carryover) changes.
- The three charts that stay charts (Budget vs Realisasi per Bulan, PO vs TF, Status) keep their chart type. `chart-monthly` and `chart-company` show money and get `fmtJutaanBulat` tooltip formatting; `chart-status` shows plain counts (`group_by_status()` in `service.py:457-462` — `statuses[status] += 1`, not an amount) and must NOT be run through `fmtJutaanBulat`.
- `fmtJutaanBulat` must be a single shared function, not duplicated — Sponsorship Dashboard's existing `_sponsorshipFormatJutaan` (`app/static/js/sponsorship.js`) is refactored to call it rather than keeping its own inline rounding logic.
- Re-check `git status --porcelain -- app/static/js/budget.js app/static/js/app.js app/static/js/sponsorship.js app/templates/budget/dashboard.html` before editing each file — all were clean at plan-writing time, but this is a shared checkout with other concurrent sessions; re-verify before every commit and never `git add -A`/`git add .`.

---

### Task 1: Shared `fmtJutaanBulat` formatter

**Files:**
- Modify: `app/static/js/app.js:513-520` (insert after the existing `fmtJutaan`)
- Modify: `app/static/js/sponsorship.js:210-213` (delegate to the new shared function)

**Interfaces:**
- Produces: `fmtJutaanBulat(n)` (global function in `app.js`) — rounds `n` to the nearest whole million and formats with Indonesian locale thousands separators, no prefix or suffix (e.g. `607473125` → `"607"`). Consumed by Tasks 2-4 and by `sponsorship.js`.

- [ ] **Step 1: Add the shared formatter**

In `app/static/js/app.js`, replace (current lines 513-520):

```javascript
function fmtRupiah(n) {
  return new Intl.NumberFormat("id-ID").format(n || 0);
}

function fmtJutaan(amount) {
  const jt = (amount || 0) / 1000000;
  return jt.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}
```

with:

```javascript
function fmtRupiah(n) {
  return new Intl.NumberFormat("id-ID").format(n || 0);
}

function fmtJutaan(amount) {
  const jt = (amount || 0) / 1000000;
  return jt.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

// Whole-million amount, no "Rp" prefix or "Jt" suffix — e.g. 607473125 -> "607".
// Shared by every dashboard that wants a plain rounded-millions number
// (Sponsorship Dashboard, Budget Dashboard).
function fmtJutaanBulat(amount) {
  const jt = Math.round((amount || 0) / 1000000);
  return jt.toLocaleString("id-ID");
}
```

- [ ] **Step 2: Refactor Sponsorship's formatter to delegate to it**

In `app/static/js/sponsorship.js`, replace (current lines 210-213):

```javascript
function _sponsorshipFormatJutaan(n) {
  const jt = Math.round((n || 0) / 1000000);
  return jt.toLocaleString("id-ID");
}
```

with:

```javascript
function _sponsorshipFormatJutaan(n) {
  return fmtJutaanBulat(n);
}
```

- [ ] **Step 3: Manual verify**

Run the dev server, open Sinar Mas Tjipta → Sponsorship → Dashboard. Confirm every amount still shows the same plain rounded-millions numbers as before this change (no visible difference — this step is a pure refactor).

- [ ] **Step 4: Commit**

```bash
git add app/static/js/app.js app/static/js/sponsorship.js
git commit -m "feat: add shared fmtJutaanBulat formatter, refactor Sponsorship to use it"
```

---

### Task 2: Per Department/Activity/Category — charts to tables

**Files:**
- Modify: `app/templates/budget/dashboard.html:32-34`
- Modify: `app/static/js/budget.js:169-180` (the three `budgetRenderBarChart` calls), and add a new `budgetRenderGroupTable` function near `budgetRenderBarChart`/`budgetRenderPieChart`.

**Interfaces:**
- Consumes: `fmtJutaanBulat` from Task 1; `data.deptChart`/`data.activityChart`/`data.categoryChart` (unchanged API shape: `{labels: string[], budget: number[], realized: number[], count: number[]}`, already sorted by budget descending server-side).
- Produces: `budgetRenderGroupTable(elId, chartData, labelHeader)` — consumed only within `budget.js`.

- [ ] **Step 1: Replace the three chart cards with table cards**

In `app/templates/budget/dashboard.html`, replace (current lines 32-34):

```html
    <div class="budget-chart-card"><h3>Per Department</h3><canvas id="chart-dept"></canvas></div>
    <div class="budget-chart-card"><h3>Per Activity</h3><canvas id="chart-activity"></canvas></div>
    <div class="budget-chart-card"><h3>Per Category</h3><canvas id="chart-category"></canvas></div>
```

with:

```html
    <div class="budget-chart-card"><h3>Per Department</h3><table class="budget-table" id="table-dept"></table></div>
    <div class="budget-chart-card"><h3>Per Activity</h3><table class="budget-table" id="table-activity"></table></div>
    <div class="budget-chart-card"><h3>Per Category</h3><table class="budget-table" id="table-category"></table></div>
```

- [ ] **Step 2: Add `budgetRenderGroupTable` and stop chart-rendering dept/activity/category**

Replace (current lines 169-180, inside `budgetLoadDashboard`):

```javascript
      budgetRenderBarChart("chart-dept", data.deptChart.labels, [
        { label: "Budget", data: data.deptChart.budget, backgroundColor: "#6366f1" },
        { label: "Realisasi", data: data.deptChart.realized, backgroundColor: "#818cf8" },
      ]);
      budgetRenderBarChart("chart-activity", data.activityChart.labels, [
        { label: "Budget", data: data.activityChart.budget, backgroundColor: "#6366f1" },
        { label: "Realisasi", data: data.activityChart.realized, backgroundColor: "#818cf8" },
      ]);
      budgetRenderBarChart("chart-category", data.categoryChart.labels, [
        { label: "Budget", data: data.categoryChart.budget, backgroundColor: "#6366f1" },
        { label: "Realisasi", data: data.categoryChart.realized, backgroundColor: "#818cf8" },
      ]);
```

with:

```javascript
      budgetRenderGroupTable("table-dept", data.deptChart, "Department");
      budgetRenderGroupTable("table-activity", data.activityChart, "Activity");
      budgetRenderGroupTable("table-category", data.categoryChart, "Category");
```

Then, immediately after the `budgetRenderPieChart` function definition (current lines 45-54), add:

```javascript
function budgetRenderGroupTable(elId, chartData, labelHeader) {
  const el = document.getElementById(elId);
  if (!chartData.labels.length) {
    el.innerHTML = '<tr><td style="text-align:center;color:var(--text-muted)">Tidak ada data.</td></tr>';
    return;
  }
  let html = "<thead><tr><th>" + labelHeader + "</th><th>Jumlah</th><th>Budget</th><th>Realisasi</th></tr></thead><tbody>";
  chartData.labels.forEach(function (label, i) {
    html += "<tr><td>" + label + "</td><td>" + chartData.count[i] + "</td><td>" +
      fmtJutaanBulat(chartData.budget[i]) + "</td><td>" + fmtJutaanBulat(chartData.realized[i]) + "</td></tr>";
  });
  html += "</tbody>";
  el.innerHTML = html;
}
```

- [ ] **Step 3: Manual verify**

Run the dev server, open Sinar Mas Tjipta → Budget → Dashboard. Confirm "Per Department", "Per Activity", "Per Category" now render as tables (Nama/Jumlah/Budget/Realisasi columns), rows ordered by Budget descending, amounts as plain rounded-millions numbers. Confirm the other three charts (Bulanan, PO vs TF, Status) still render as charts, unaffected.

- [ ] **Step 4: Commit**

```bash
git add app/templates/budget/dashboard.html app/static/js/budget.js
git commit -m "feat: replace Budget dashboard dept/activity/category charts with sorted tables"
```

---

### Task 3: Dynamic filter — remove the button, apply on change

**Files:**
- Modify: `app/templates/budget/dashboard.html:24`
- Modify: `app/static/js/budget.js:191-194` (`initBudgetDashboard`)

**Interfaces:**
- Consumes: `budgetLoadDashboard()` (unchanged, already exists).

**Note:** re-check `git status --porcelain -- app/templates/budget/dashboard.html app/static/js/budget.js` — Task 2 already modified both of these files in this same plan; if Task 2's commit landed, these edits apply to the post-Task-2 state.

- [ ] **Step 1: Remove the "Terapkan Filter" button**

In `app/templates/budget/dashboard.html`, replace (current line 24):

```html
    <button class="budget-btn" id="bf-apply">Terapkan Filter</button>
```

with nothing (delete the line).

- [ ] **Step 2: Wire each filter select to reload on change**

In `app/static/js/budget.js`, replace (current lines 191-194):

```javascript
function initBudgetDashboard() {
  budgetLoadLookups().then(budgetLoadDashboard);
  document.getElementById("bf-apply").addEventListener("click", budgetLoadDashboard);
}
```

with:

```javascript
function initBudgetDashboard() {
  budgetLoadLookups().then(budgetLoadDashboard);
  ["bf-company", "bf-dept", "bf-year", "bf-category", "bf-activity"].forEach(function (id) {
    document.getElementById(id).addEventListener("change", budgetLoadDashboard);
  });
}
```

- [ ] **Step 3: Manual verify**

On the running dev server's Budget Dashboard, change each of the 5 filters one at a time (Company, Dept, Tahun, Kategori, Aktivitas) — confirm the dashboard reloads immediately on each change with no button to click, and that there is no "Terapkan Filter" button visible anywhere on the page.

- [ ] **Step 4: Commit**

```bash
git add app/templates/budget/dashboard.html app/static/js/budget.js
git commit -m "feat: apply Budget dashboard filters on change, remove Terapkan Filter button"
```

---

### Task 4: Format every remaining amount on the page

**Files:**
- Modify: `app/static/js/budget.js` — `budgetRenderSummary` (currently lines 56-71), `budgetRenderExpiredAnalysis` (currently lines 73-104), `budgetRenderCompliance` (currently lines 106-121), `budgetRenderBarChart` (currently lines 27-43), `budgetRenderPieChart` (currently lines 45-54), and its two call sites (currently lines 181-184).

**Interfaces:**
- Consumes: `fmtJutaanBulat` from Task 1.

**Note:** re-check current line numbers with `grep -n` before editing — Tasks 2-3 already touched this file earlier in this plan, shifting some line numbers.

- [ ] **Step 1: Summary cards**

Replace:

```javascript
function budgetRenderSummary(summary) {
  const el = document.getElementById("budget-summary");
  const cards = [
    ["Total Budget", summary.formatted.totalBudget],
    ["Total Realisasi", summary.formatted.totalRealized],
    ["Sisa", summary.formatted.remaining],
    ["Utilisasi Rata-rata", summary.formatted.avgUtilization],
    ["Expired", summary.totalExpired],
    ["Near Limit", summary.totalNearLimit],
    ["Active", summary.totalActive],
  ];
```

with:

```javascript
function budgetRenderSummary(summary) {
  const el = document.getElementById("budget-summary");
  const cards = [
    ["Total Budget", fmtJutaanBulat(summary.totalBudget)],
    ["Total Realisasi", fmtJutaanBulat(summary.totalRealized)],
    ["Sisa", fmtJutaanBulat(summary.remaining)],
    ["Utilisasi Rata-rata", summary.formatted.avgUtilization],
    ["Expired", summary.totalExpired],
    ["Near Limit", summary.totalNearLimit],
    ["Active", summary.totalActive],
  ];
```

(`avgUtilization` is a percentage, not a currency amount — left as the backend-formatted `"XX.X%"` string, unchanged.)

- [ ] **Step 2: Expired-analysis cards and breakdown tables**

Replace:

```javascript
function budgetRenderExpiredAnalysis(expiredAnalysis) {
  const summaryEl = document.getElementById("budget-expired-summary");
  const cards = [
    ["Total Expired", expiredAnalysis.totalExpired],
    ["Total Amount", "Rp " + fmtRupiah(expiredAnalysis.totalAmount)],
    ["Total Realized", "Rp " + fmtRupiah(expiredAnalysis.totalRealized)],
    ["≤30 Hari", expiredAnalysis.ageBuckets.recent],
    ["31-90 Hari", expiredAnalysis.ageBuckets.midterm],
    [">90 Hari", expiredAnalysis.ageBuckets.longterm],
  ];
  summaryEl.innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");

  function renderBreakdownTable(elId, rows, labelKey, labelHeader) {
    const el = document.getElementById(elId);
    if (!rows.length) {
      el.innerHTML = '<tr><td style="text-align:center;color:var(--text-muted)">Tidak ada data expired.</td></tr>';
      return;
    }
    let html = "<thead><tr><th>" + labelHeader + "</th><th>Jumlah</th><th>Amount</th><th>Realized</th></tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr><td>" + r[labelKey] + "</td><td>" + r.count + "</td><td>Rp " +
        fmtRupiah(r.amount) + "</td><td>Rp " + fmtRupiah(r.realized) + "</td></tr>";
    });
    html += "</tbody>";
    el.innerHTML = html;
  }
```

with:

```javascript
function budgetRenderExpiredAnalysis(expiredAnalysis) {
  const summaryEl = document.getElementById("budget-expired-summary");
  const cards = [
    ["Total Expired", expiredAnalysis.totalExpired],
    ["Total Amount", fmtJutaanBulat(expiredAnalysis.totalAmount)],
    ["Total Realized", fmtJutaanBulat(expiredAnalysis.totalRealized)],
    ["≤30 Hari", expiredAnalysis.ageBuckets.recent],
    ["31-90 Hari", expiredAnalysis.ageBuckets.midterm],
    [">90 Hari", expiredAnalysis.ageBuckets.longterm],
  ];
  summaryEl.innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");

  function renderBreakdownTable(elId, rows, labelKey, labelHeader) {
    const el = document.getElementById(elId);
    if (!rows.length) {
      el.innerHTML = '<tr><td style="text-align:center;color:var(--text-muted)">Tidak ada data expired.</td></tr>';
      return;
    }
    let html = "<thead><tr><th>" + labelHeader + "</th><th>Jumlah</th><th>Amount</th><th>Realized</th></tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr><td>" + r[labelKey] + "</td><td>" + r.count + "</td><td>" +
        fmtJutaanBulat(r.amount) + "</td><td>" + fmtJutaanBulat(r.realized) + "</td></tr>";
    });
    html += "</tbody>";
    el.innerHTML = html;
  }
```

- [ ] **Step 3: Compliance cards**

Replace:

```javascript
    ["Additional Disetujui", complianceData.additionalApproved + " (Rp " + fmtRupiah(complianceData.additionalAmountApproved) + ")"],
```

with:

```javascript
    ["Additional Disetujui", complianceData.additionalApproved + " (" + fmtJutaanBulat(complianceData.additionalAmountApproved) + ")"],
```

- [ ] **Step 4: Tooltip formatting on the remaining charts**

`chart-status` shows plain counts (`group_by_status()` in `service.py` — `statuses[status] += 1`), not money, so `budgetRenderPieChart` takes a new optional formatter parameter instead of always applying `fmtJutaanBulat` — callers that show money pass `fmtJutaanBulat`, `chart-status`'s caller passes nothing (defaults to showing the raw value, same as today).

Replace:

```javascript
function budgetRenderBarChart(canvasId, labels, datasets) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (budgetCharts[canvasId]) budgetCharts[canvasId].destroy();
  budgetCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e2e8f0" } } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
      },
    },
  });
}

function budgetRenderPieChart(canvasId, labels, values, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (budgetCharts[canvasId]) budgetCharts[canvasId].destroy();
  budgetCharts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
    options: { responsive: true, plugins: { legend: { labels: { color: "#e2e8f0" } } } },
  });
}
```

with:

```javascript
function budgetRenderBarChart(canvasId, labels, datasets) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (budgetCharts[canvasId]) budgetCharts[canvasId].destroy();
  budgetCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#e2e8f0" } },
        tooltip: { callbacks: { label: c => c.dataset.label + ": " + fmtJutaanBulat(c.parsed.y) } },
      },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
      },
    },
  });
}

function budgetRenderPieChart(canvasId, labels, values, colors, formatValue) {
  const fmt = formatValue || function (v) { return v; };
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (budgetCharts[canvasId]) budgetCharts[canvasId].destroy();
  budgetCharts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#e2e8f0" } },
        tooltip: { callbacks: { label: c => c.label + ": " + fmt(c.parsed) } },
      },
    },
  });
}
```

Then replace the two `budgetRenderPieChart` call sites (currently lines 181-184):

```javascript
      budgetRenderPieChart("chart-company", data.companyChart.labels, data.companyChart.budget,
        ["#f97316", "#06b6d4"]);
      budgetRenderPieChart("chart-status", data.statusChart.labels, data.statusChart.values,
        ["#10b981", "#f59e0b", "#ef4444", "#3b82f6"]);
```

with:

```javascript
      budgetRenderPieChart("chart-company", data.companyChart.labels, data.companyChart.budget,
        ["#f97316", "#06b6d4"], fmtJutaanBulat);
      budgetRenderPieChart("chart-status", data.statusChart.labels, data.statusChart.values,
        ["#10b981", "#f59e0b", "#ef4444", "#3b82f6"]);
```

(`chart-monthly`, the only remaining `budgetRenderBarChart` caller, shows Budget/Realisasi — always money — so `budgetRenderBarChart`'s tooltip formatting is unconditional, no parameter needed there.)

- [ ] **Step 5: Manual verify**

On the running dev server's Budget Dashboard: confirm no amount anywhere on the page shows "Rp" or a raw unrounded number — summary cards, Expired Analysis cards, both Expired breakdown tables, Compliance card, the three new group tables (Task 2), and hovering the "Budget vs Realisasi per Bulan" and "PO vs TF" chart tooltips. Confirm `chart-status`'s tooltip still shows plain counts (e.g. "Active: 12"), not divided by a million.

- [ ] **Step 6: Commit**

```bash
git add app/static/js/budget.js
git commit -m "feat: format remaining Budget dashboard amounts as plain rounded-millions numbers"
```

---

### Task 5: Final review

**Files:** None (verification only).

- [ ] **Step 1: Re-read the diff against the spec**

Review the cumulative diff from Tasks 1-4 against
`docs/superpowers/specs/2026-08-04-budget-dashboard-tables-dynamic-filter-amount-format-design.md`
— confirm every design decision (table columns, dynamic filter, shared
formatter, which charts stay charts, `chart-status` staying unformatted)
is reflected in the actual code, and that no other Budget tab or backend
file was touched.
