# Budget Dashboard Missing Insights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display the `expiredAnalysis` and `complianceData` insights the Budget Dashboard's API already computes and sends to the browser, but which `budget.js` currently never reads and `dashboard.html` never has a section for.

**Architecture:** Two new `.budget-card` sections in `dashboard.html`, each populated by a new render function in `budget.js` (matching the existing `.budget-stat-card`/`.budget-table` markup conventions already used on this page), wired into the existing `budgetLoadDashboard()` fetch callback. No backend change — `/budget/api/dashboard-data` already returns both fields.

**Tech Stack:** Flask/Jinja2, vanilla JS, pytest.

## Global Constraints

- No change to `analyze_expired_budgets`/`analyze_compliance`/`get_dashboard_data` — both analyses are already correct; only their presentation is added.
- No new chart type — both sections use `.budget-stat-card` (via `.budget-summary-grid`) and plain `.budget-table` markup, matching the rest of this page.
- Amounts are formatted client-side with the existing global `fmtRupiah()` (from `app.js`, already loaded on every page) plus a `"Rp "` prefix — no backend formatting change.
- Only these files change: `app/templates/budget/dashboard.html`, `app/static/js/budget.js`, `app/tests/test_budget_routes.py`.

---

### Task 1: "Analisis Budget Expired" section

**Files:**
- Modify: `app/templates/budget/dashboard.html:36-37` (insert point, right after the existing `.budget-chart-grid`'s closing `</div>` and before the Notifikasi card)
- Modify: `app/static/js/budget.js:71-72` (insert point, right after `budgetRenderSummary`) and `:110-133` (`budgetLoadDashboard`'s fetch callback)
- Test: `app/tests/test_budget_routes.py`

**Interfaces:**
- Produces: `budgetRenderExpiredAnalysis(expiredAnalysis)` — consumed by Task 2's final wiring review (both new functions are called from the same callback).

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_budget_routes.py`:

```python
def test_dashboard_page_has_expired_analysis_section(client):
    login(client)
    resp = client.get("/budget/")
    assert resp.status_code == 200
    assert b'id="budget-expired-summary"' in resp.data
    assert b"budgetRenderExpiredAnalysis" in resp.data
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k expired_analysis_section`
Expected: FAIL — neither `budget-expired-summary` nor `budgetRenderExpiredAnalysis` exist yet.

- [ ] **Step 3: Add the HTML section**

In `app/templates/budget/dashboard.html`, replace:

```html
  <div class="budget-chart-grid">
    <div class="budget-chart-card"><h3>Budget vs Realisasi per Bulan</h3><canvas id="chart-monthly"></canvas></div>
    <div class="budget-chart-card"><h3>PO vs TF</h3><canvas id="chart-company"></canvas></div>
    <div class="budget-chart-card"><h3>Per Department</h3><canvas id="chart-dept"></canvas></div>
    <div class="budget-chart-card"><h3>Per Activity</h3><canvas id="chart-activity"></canvas></div>
    <div class="budget-chart-card"><h3>Per Category</h3><canvas id="chart-category"></canvas></div>
    <div class="budget-chart-card"><h3>Status</h3><canvas id="chart-status"></canvas></div>
  </div>

  <div class="budget-card">
    <h3>Notifikasi</h3>
    <ul id="budget-notifications"></ul>
  </div>
```

with:

```html
  <div class="budget-chart-grid">
    <div class="budget-chart-card"><h3>Budget vs Realisasi per Bulan</h3><canvas id="chart-monthly"></canvas></div>
    <div class="budget-chart-card"><h3>PO vs TF</h3><canvas id="chart-company"></canvas></div>
    <div class="budget-chart-card"><h3>Per Department</h3><canvas id="chart-dept"></canvas></div>
    <div class="budget-chart-card"><h3>Per Activity</h3><canvas id="chart-activity"></canvas></div>
    <div class="budget-chart-card"><h3>Per Category</h3><canvas id="chart-category"></canvas></div>
    <div class="budget-chart-card"><h3>Status</h3><canvas id="chart-status"></canvas></div>
  </div>

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

  <div class="budget-card">
    <h3>Notifikasi</h3>
    <ul id="budget-notifications"></ul>
  </div>
```

- [ ] **Step 4: Add `budgetRenderExpiredAnalysis()`**

In `app/static/js/budget.js`, replace:

```javascript
function budgetRenderNotifications(notifications) {
```

with:

```javascript
function budgetRenderExpiredAnalysis(expiredAnalysis) {
  const summaryEl = document.getElementById("budget-expired-summary");
  const cards = [
    ["Total Expired", expiredAnalysis.totalExpired],
    ["Total Amount", "Rp " + fmtRupiah(expiredAnalysis.totalAmount)],
    ["Total Realized", "Rp " + fmtRupiah(expiredAnalysis.totalRealized)],
    ["\u226430 Hari", expiredAnalysis.ageBuckets.recent],
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
  renderBreakdownTable("budget-expired-dept-table", expiredAnalysis.byDept, "dept", "Department");
  renderBreakdownTable("budget-expired-company-table", expiredAnalysis.byCompany, "company", "Company");
}

function budgetRenderNotifications(notifications) {
```

- [ ] **Step 5: Wire it into the dashboard load callback**

In `app/static/js/budget.js`, replace:

```javascript
      budgetRenderSummary(data.summary);
      budgetRenderNotifications(data.notifications);
```

with:

```javascript
      budgetRenderSummary(data.summary);
      budgetRenderExpiredAnalysis(data.expiredAnalysis);
      budgetRenderNotifications(data.notifications);
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k expired_analysis_section`
Expected: PASS

- [ ] **Step 7: Run the full Budget test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
cd C:\Financehub
git add app/templates/budget/dashboard.html app/static/js/budget.js app/tests/test_budget_routes.py
git commit -m "feat: surface Expired Budget Analysis on the Budget Dashboard"
```

---

### Task 2: "Compliance Carryover/Tambahan" section + final verification

**Files:**
- Modify: `app/templates/budget/dashboard.html` (insert point, right after Task 1's new "Analisis Budget Expired" card)
- Modify: `app/static/js/budget.js` (insert point, right after `budgetRenderExpiredAnalysis`) and the `budgetLoadDashboard` callback again
- Test: `app/tests/test_budget_routes.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (independent section), but shares the same fetch callback insertion point — apply this task's edit after Task 1's is already in place.

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_budget_routes.py`:

```python
def test_dashboard_page_has_compliance_section(client):
    login(client)
    resp = client.get("/budget/")
    assert resp.status_code == 200
    assert b'id="budget-compliance-summary"' in resp.data
    assert b"budgetRenderCompliance" in resp.data


def test_dashboard_api_still_returns_expired_and_compliance_keys(client):
    login(client)
    resp = client.get("/budget/api/dashboard-data")
    data = resp.get_json()
    assert "expiredAnalysis" in data
    assert "complianceData" in data
    assert "ageBuckets" in data["expiredAnalysis"]
    assert "complianceRate" in data["complianceData"]
```

- [ ] **Step 2: Run the test to verify the new-section test fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k "compliance_section or still_returns_expired"`
Expected: `test_dashboard_page_has_compliance_section` FAILs (section doesn't exist yet); `test_dashboard_api_still_returns_expired_and_compliance_keys` PASSes already (the backend already returns these — this second test is a regression guard for Task 1, not new behavior for Task 2).

- [ ] **Step 3: Add the HTML section**

In `app/templates/budget/dashboard.html`, replace:

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

  <div class="budget-card">
    <h3>Notifikasi</h3>
```

with:

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

  <div class="budget-card">
    <h3>Compliance Carryover/Tambahan</h3>
    <div class="budget-summary-grid" id="budget-compliance-summary"></div>
  </div>

  <div class="budget-card">
    <h3>Notifikasi</h3>
```

- [ ] **Step 4: Add `budgetRenderCompliance()`**

In `app/static/js/budget.js`, replace:

```javascript
function budgetRenderNotifications(notifications) {
```

with:

```javascript
function budgetRenderCompliance(complianceData) {
  const el = document.getElementById("budget-compliance-summary");
  const cards = [
    ["Compliance Rate", complianceData.complianceRate + "%"],
    ["Total Requests", complianceData.totalRequests],
    ["Approved", complianceData.approved],
    ["Pending", complianceData.pending],
    ["Rejected", complianceData.rejected],
    ["Carryover / Additional", complianceData.carryoverCount + " / " + complianceData.additionalCount],
    ["Additional Disetujui", complianceData.additionalApproved + " (Rp " + fmtRupiah(complianceData.additionalAmountApproved) + ")"],
  ];
  el.innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
}

function budgetRenderNotifications(notifications) {
```

- [ ] **Step 5: Wire it into the dashboard load callback**

In `app/static/js/budget.js`, replace:

```javascript
      budgetRenderSummary(data.summary);
      budgetRenderExpiredAnalysis(data.expiredAnalysis);
      budgetRenderNotifications(data.notifications);
```

with:

```javascript
      budgetRenderSummary(data.summary);
      budgetRenderExpiredAnalysis(data.expiredAnalysis);
      budgetRenderCompliance(data.complianceData);
      budgetRenderNotifications(data.notifications);
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k "compliance_section or still_returns_expired or expired_analysis_section"`
Expected: all 3 PASS.

- [ ] **Step 7: Run the full test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/ -q`
Expected: same pass/fail counts as before this plan aside from the 3 tests it added (pre-existing failures are documented as unrelated Windows SQLite file-lock flakiness in `01 - Proyek/FinanceHub/FinanceHub - Known Issues.md` in the Obsidian vault).

- [ ] **Step 8: Manual check**

Open Budget Dashboard. Create (or find existing) at least one Expired budget and one Carryover/Additional request in various statuses (via Kelola Budget / Carryover tabs if needed for test data). Confirm "Analisis Budget Expired" shows real, non-zero numbers matching what's visible in Kelola Budget, and the department/company tables list the correct rows. Confirm "Compliance Carryover/Tambahan" shows a sensible percentage and counts matching what's visible in the Carryover/Tambahan tab. Apply a filter (e.g. select one company) and confirm both new sections update along with the existing charts.

- [ ] **Step 9: Commit**

```bash
cd C:\Financehub
git add app/templates/budget/dashboard.html app/static/js/budget.js app/tests/test_budget_routes.py
git commit -m "feat: surface Compliance Carryover/Tambahan data on the Budget Dashboard"
```

## Out of Scope

- Kelola Budget, Kelola Realisasi, Carryover/Tambahan tabs.
- Any change to `analyze_expired_budgets`/`analyze_compliance`/`get_dashboard_data`.
- Any new chart type.
