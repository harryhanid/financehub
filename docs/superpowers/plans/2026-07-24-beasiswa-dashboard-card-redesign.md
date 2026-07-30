# Beasiswa Dashboard Card Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Beasiswa Dashboard tab its own visual identity — tint-per-semantic summary cards and grouped neutral chart cards — replacing its reuse of shared `.budget-stat-card`/`.budget-chart-card`/`.budget-summary-grid`/`.setf-grafik-grid` classes with new page-specific ones, without touching those shared classes or the two other pages (Sahabat ETF, Budget Monitoring dashboard) that consume them.

**Architecture:** A new standalone stylesheet (`beasiswa_dashboard.css`) defines all new classes and is linked only from `beasiswa/index.html`. The template's Ringkasan and Grafik section markup gets its class names swapped to the new ones, with 2 new section-label `<div>`s inserted to group the 9 chart/table cards into 3 visual clusters. `dashboard_beasiswa.js`'s two summary-card-rendering functions get their generated class strings updated to match. No backend, no data flow, no JS control-flow changes.

**Tech Stack:** Flask + Jinja2 template with inline vanilla JS, plain CSS (no build step, no CSS framework).

**Spec:** `docs/superpowers/specs/2026-07-24-beasiswa-dashboard-card-redesign-design.md`

## Global Constraints

- New classes only live in the new `beasiswa_dashboard.css` file and are only referenced from `templates/beasiswa/index.html` and `static/js/dashboard_beasiswa.js` — no other template or JS file changes.
- Zero changes to `budget.css`, `templates/sahabat_etf/index.html`, or `templates/budget/dashboard.html` — verified by diff/grep at the end.
- Sisa Budget card gets the negative-value tint (`.tint-negative`) only when the total is negative — mirrors the existing conditional logic (`totalSisa < 0 ? " setf-sisa-negative" : ""`), not a new behavior.
- No frontend test framework exists in this codebase — verification is app-boot + force-render + structural grep-checks, matching the pattern already established in this session's prior template-only tasks.
- Confirmed: Beasiswa Dashboard has no print/export-PDF trigger (`grep` for `window.print`/`Export PDF`/`setf-print-header` in `beasiswa/index.html` returns nothing — that feature exists only on Sahabat ETF). The `@media print` rules in `budget.css` that reference `.setf-grafik-grid`/`.budget-summary-grid`/`.budget-chart-card` are therefore irrelevant to this page and do not need to be copied into the new file.

---

## Task 1: Create `beasiswa_dashboard.css`

**Files:**
- Create: `app/static/css/beasiswa_dashboard.css`

**Interfaces:**
- Produces: CSS classes `.beasiswa-dash-summary-grid`, `.beasiswa-dash-stat-card` (+ `.tint-budget`/`.tint-klaim`/`.tint-realisasi`/`.tint-negative` modifiers), `.beasiswa-dash-grafik-grid`, `.beasiswa-dash-section-label`, `.beasiswa-dash-chart-card` (+ `.compact` modifier) — consumed by Task 2 (template) and Task 3 (JS).

- [ ] **Step 1: Write the file**

Create `app/static/css/beasiswa_dashboard.css` with this exact content:

```css
/* static/css/beasiswa_dashboard.css — Beasiswa Dashboard tab, page-specific.
   Not shared with Sahabat ETF or Budget Monitoring dashboard (both still use
   the generic .budget-* classes in budget.css) — see
   docs/superpowers/specs/2026-07-24-beasiswa-dashboard-card-redesign-design.md */

/* ── Layout containers ─────────────────────────────────────────────────── */
.beasiswa-dash-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

/* Fixed 2-column pairing (bulan/tahun, monthly-compare/kategori, etc.) rather
   than auto-fit, which would flow all 9 cards into 3-4 columns on a wide
   viewport and break the pairing — carried over from .setf-grafik-grid. */
.beasiswa-dash-grafik-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.beasiswa-dash-grafik-grid .beasiswa-dash-chart-card {
  min-width: 0;
}
.beasiswa-dash-grafik-grid canvas {
  max-width: 100%;
}
@media (max-width: 700px) {
  .beasiswa-dash-grafik-grid {
    grid-template-columns: 1fr;
  }
}

/* ── Section grouping labels inside the grafik grid ──────────────────────── */
.beasiswa-dash-section-label {
  grid-column: 1 / -1;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin: 0.6rem 0 0.1rem;
  padding-top: 0.4rem;
  border-top: 1px solid var(--border-color);
}
.beasiswa-dash-section-label:first-child {
  border-top: none;
  padding-top: 0;
  margin-top: 0;
}

/* ── Summary stat cards — base + tint modifiers ──────────────────────────── */
.beasiswa-dash-stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1rem 1.1rem;
}
.beasiswa-dash-stat-card .label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.beasiswa-dash-stat-card .value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-top: 0.25rem;
}

.beasiswa-dash-stat-card.tint-budget     { background: #eff6ff; border-color: #bfdbfe; }
.beasiswa-dash-stat-card.tint-budget     .value { color: #1d4ed8; }
.beasiswa-dash-stat-card.tint-klaim      { background: #fffbeb; border-color: #fde68a; }
.beasiswa-dash-stat-card.tint-klaim      .value { color: #b45309; }
.beasiswa-dash-stat-card.tint-realisasi  { background: #f0fdf4; border-color: #bbf7d0; }
.beasiswa-dash-stat-card.tint-realisasi  .value { color: #15803d; }
.beasiswa-dash-stat-card.tint-negative   { background: #fef2f2; border-color: #fecaca; }
.beasiswa-dash-stat-card.tint-negative   .value { color: #b91c1c; }

/* ── Chart/table cards — neutral, uniform ────────────────────────────────── */
.beasiswa-dash-chart-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 1rem;
  border-top: 3px solid var(--border-color);
  box-shadow: 0 1px 2px rgba(15, 23, 42, .05);
}
.beasiswa-dash-chart-card canvas {
  max-height: 260px;
}

/* Compact cards (tables): smaller heading, denser rows, capped scroll height —
   carried over unchanged from .setf-compact-card / .setf-compact-scroll in
   budget.css (that scroll wrapper class itself is untouched in the markup). */
.beasiswa-dash-chart-card.compact h3 {
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}
.beasiswa-dash-chart-card.compact table th,
.beasiswa-dash-chart-card.compact table td {
  padding: 0.35rem 0.6rem;
  font-size: 0.8rem;
}
.beasiswa-dash-chart-card.compact table thead th {
  position: sticky;
  top: 0;
  background: var(--bg-card);
}
```

- [ ] **Step 2: Confirm the file was created correctly**

Run: `cd app && python3 -c "print(open('static/css/beasiswa_dashboard.css', encoding='utf-8').read().count('{') == open('static/css/beasiswa_dashboard.css', encoding='utf-8').read().count('}'))"`
Expected: `True` (braces balanced — catches a truncated paste).

- [ ] **Step 3: Commit**

```bash
git add app/static/css/beasiswa_dashboard.css
git commit -m "feat: add beasiswa_dashboard.css for page-specific card styling"
```

---

## Task 2: Update `beasiswa/index.html` markup

**Files:**
- Modify: `app/templates/beasiswa/index.html:1-7` (head block — link the new stylesheet)
- Modify: `app/templates/beasiswa/index.html:105` (Ringkasan summary grid div)
- Modify: `app/templates/beasiswa/index.html:109-188` (Grafik section: grid class + 9 chart-card divs + 2 new section-label divs)

**Interfaces:**
- Consumes: CSS classes from Task 1 (`.beasiswa-dash-summary-grid`, `.beasiswa-dash-grafik-grid`, `.beasiswa-dash-section-label`, `.beasiswa-dash-chart-card`, `.compact`)
- Produces: rendered markup that Task 3's JS-generated summary cards attach into (`#dash-summary` div, unchanged id)

- [ ] **Step 1: Link the new stylesheet**

In `app/templates/beasiswa/index.html`, find (lines 3-7):

```html
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
{% endblock %}
```

Replace with:

```html
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/beasiswa_dashboard.css') }}">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
{% endblock %}
```

(`budget.css` stays linked — `.budget-page`, `.setf-accordion`, `.setf-compact-scroll`, `.filter-bar`, `.setf-filter-field-wide`, etc. are all still used by this page and untouched.)

- [ ] **Step 2: Rename the Ringkasan summary grid class**

Find (line 105):

```html
          <div class="budget-summary-grid" id="dash-summary"></div>
```

Replace with:

```html
          <div class="beasiswa-dash-summary-grid" id="dash-summary"></div>
```

- [ ] **Step 3: Rename the Grafik section grid + all 9 chart-card divs, add 2 section labels**

Find (lines 109-188):

```html
      <details class="setf-accordion" id="dash-grafik-accordion" open>
        <summary>Grafik</summary>
        <div class="setf-accordion-body">
          <div class="setf-grafik-grid">
            <div class="budget-chart-card"><h3>Trend per Bulan</h3><canvas id="dash-chart-bulanan"></canvas></div>
            <div class="budget-chart-card"><h3>Trend per Tahun</h3><canvas id="dash-chart-tahunan"></canvas></div>

            <div class="budget-chart-card setf-compact-card">
              <h3>Perbandingan Realisasi per Bulan per Tahun</h3>
              <div class="setf-compact-scroll">
                <table id="dash-monthly-table">
                  <thead><tr id="dash-monthly-thead-row"><th>Bulan</th></tr></thead>
                  <tbody><tr><td style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>
            
            <div class="budget-chart-card"><h3>Realisasi per Kategori</h3><canvas id="dash-chart-kategori"></canvas></div>
            <div class="budget-chart-card setf-compact-card">
              <h3>Realisasi per Kategori (Tabel)</h3>
              <div class="setf-compact-scroll">
                <table id="dash-kategori-table">
                  <thead><tr><th>Kategori</th><th>Budget</th><th>Realisasi</th><th>Sisa</th></tr></thead>
                  <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>

            <div class="budget-chart-card setf-compact-card">
              <h3>Realisasi per Jenjang Studi</h3>
              <div class="setf-compact-scroll">
                <table id="dash-jenjang-table">
                  <thead><tr><th>Jenjang</th><th class="num-right">Budget</th><th class="num-right">Realisasi</th><th class="num-right">Sisa</th></tr></thead>
                  <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>

            <div class="budget-chart-card setf-compact-card">
              <h3>Realisasi per Pillar per Tahun</h3>
              <div class="setf-compact-scroll">
                <table id="dash-pillar-year-table">
                  <thead><tr id="dash-pillar-year-thead"><th>Pillar</th></tr></thead>
                  <tbody><tr><td style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>

            <div class="budget-chart-card setf-compact-card">
              <h3>20 Transaksi Terakhir</h3>
              <div class="setf-compact-scroll" style="max-height: 550px;">
                <table id="dash-latest-payments-table">
                  <thead>
                    <tr>
                      <th>Tanggal</th>
                      <th>Nama</th>
                      <th>Kategori</th>
                      <th>Kategori 2</th>
                      <th class="num-right">Realisasi</th>
                    </tr>
                  </thead>
                  <tbody><tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>

            <div class="budget-chart-card setf-compact-card">
              <h3>Rincian Budget vs Realisasi per Program</h3>
              <div class="setf-compact-scroll">
                <table id="dash-program-table">
                  <thead>
                    <tr><th>Program</th><th class="num-right">Budget</th><th class="num-right">Payment</th><th class="num-right">Sisa</th></tr>
                  </thead>
                  <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </details>
```

Replace with (grid class renamed, all `budget-chart-card`→`beasiswa-dash-chart-card`, `setf-compact-card`→`compact`, `setf-compact-scroll` left as-is, 3 section-label divs inserted, all `id`s and table content unchanged):

```html
      <details class="setf-accordion" id="dash-grafik-accordion" open>
        <summary>Grafik</summary>
        <div class="setf-accordion-body">
          <div class="beasiswa-dash-grafik-grid">
            <div class="beasiswa-dash-section-label">Trend</div>
            <div class="beasiswa-dash-chart-card"><h3>Trend per Bulan</h3><canvas id="dash-chart-bulanan"></canvas></div>
            <div class="beasiswa-dash-chart-card"><h3>Trend per Tahun</h3><canvas id="dash-chart-tahunan"></canvas></div>

            <div class="beasiswa-dash-chart-card compact">
              <h3>Perbandingan Realisasi per Bulan per Tahun</h3>
              <div class="setf-compact-scroll">
                <table id="dash-monthly-table">
                  <thead><tr id="dash-monthly-thead-row"><th>Bulan</th></tr></thead>
                  <tbody><tr><td style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>

            <div class="beasiswa-dash-section-label">Breakdown Realisasi</div>
            <div class="beasiswa-dash-chart-card"><h3>Realisasi per Kategori</h3><canvas id="dash-chart-kategori"></canvas></div>
            <div class="beasiswa-dash-chart-card compact">
              <h3>Realisasi per Kategori (Tabel)</h3>
              <div class="setf-compact-scroll">
                <table id="dash-kategori-table">
                  <thead><tr><th>Kategori</th><th>Budget</th><th>Realisasi</th><th>Sisa</th></tr></thead>
                  <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>

            <div class="beasiswa-dash-chart-card compact">
              <h3>Realisasi per Jenjang Studi</h3>
              <div class="setf-compact-scroll">
                <table id="dash-jenjang-table">
                  <thead><tr><th>Jenjang</th><th class="num-right">Budget</th><th class="num-right">Realisasi</th><th class="num-right">Sisa</th></tr></thead>
                  <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>

            <div class="beasiswa-dash-chart-card compact">
              <h3>Realisasi per Pillar per Tahun</h3>
              <div class="setf-compact-scroll">
                <table id="dash-pillar-year-table">
                  <thead><tr id="dash-pillar-year-thead"><th>Pillar</th></tr></thead>
                  <tbody><tr><td style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>

            <div class="beasiswa-dash-section-label">Detail Transaksi</div>
            <div class="beasiswa-dash-chart-card compact">
              <h3>20 Transaksi Terakhir</h3>
              <div class="setf-compact-scroll" style="max-height: 550px;">
                <table id="dash-latest-payments-table">
                  <thead>
                    <tr>
                      <th>Tanggal</th>
                      <th>Nama</th>
                      <th>Kategori</th>
                      <th>Kategori 2</th>
                      <th class="num-right">Realisasi</th>
                    </tr>
                  </thead>
                  <tbody><tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>

            <div class="beasiswa-dash-chart-card compact">
              <h3>Rincian Budget vs Realisasi per Program</h3>
              <div class="setf-compact-scroll">
                <table id="dash-program-table">
                  <thead>
                    <tr><th>Program</th><th class="num-right">Budget</th><th class="num-right">Payment</th><th class="num-right">Sisa</th></tr>
                  </thead>
                  <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </details>
```

- [ ] **Step 4: App-boot and force-render sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
with app.test_client() as c:
    with c.session_transaction() as sess:
        pass
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`, no exceptions (this confirms Jinja can still parse the template — a rendered-with-session request isn't required to catch a template syntax error).

- [ ] **Step 5: Grep-confirm the rename is complete inside this file**

Run: `cd app && grep -c "budget-chart-card\|budget-summary-grid\|setf-grafik-grid" templates/beasiswa/index.html`
Expected: `0`

Run: `cd app && grep -c "beasiswa-dash-chart-card" templates/beasiswa/index.html`
Expected: `9` (one per chart/table card)

- [ ] **Step 6: Commit**

```bash
git add app/templates/beasiswa/index.html
git commit -m "feat: migrate Beasiswa Dashboard markup to page-specific card classes"
```

---

## Task 3: Update `dashboard_beasiswa.js` summary card rendering

**Files:**
- Modify: `app/static/js/dashboard_beasiswa.js:148-172` (`dashRenderSummaryCards`, `dashRenderSummarySkeleton`)

**Interfaces:**
- Consumes: CSS classes from Task 1 (`.beasiswa-dash-stat-card`, `.tint-budget`, `.tint-klaim`, `.tint-realisasi`, `.tint-negative`)
- Produces: no change to function signatures or call sites — `dashRenderSummaryCards(rows)` and `dashRenderSummarySkeleton()` keep being called exactly as they are today from `loadDashboard()`

- [ ] **Step 1: Update the modifier strings and base class**

In `app/static/js/dashboard_beasiswa.js`, find (lines 148-165):

```javascript
function dashRenderSummaryCards(rows) {
  const totalSiswa = rows.filter(function (r) { return r.status === "Aktif"; }).length;
  const totalBudget = rows.reduce(function (s, r) { return s + r.budget_total; }, 0);
  const totalPayment = rows.reduce(function (s, r) { return s + r.payment_total; }, 0);
  const totalRealisasi = rows.reduce(function (s, r) { return s + r.realisasi_total; }, 0);
  const totalSisa = rows.reduce(function (s, r) { return s + r.sisa_budget; }, 0);
  const cards = [
    ["Total Siswa Aktif", totalSiswa, ""],
    ["Total Budget", dashFmtJutaan(totalBudget), ""],
    ["Total Klaim", dashFmtJutaan(totalPayment), ""],
    ["Total Realisasi", dashFmtJutaan(totalRealisasi), " setf-stat-realisasi"],
    ["Sisa Budget", dashFmtJutaan(totalSisa), totalSisa < 0 ? " setf-sisa-negative" : ""],
  ];
  document.getElementById("dash-summary").innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card' + c[2] + '"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
}
```

Replace with:

```javascript
function dashRenderSummaryCards(rows) {
  const totalSiswa = rows.filter(function (r) { return r.status === "Aktif"; }).length;
  const totalBudget = rows.reduce(function (s, r) { return s + r.budget_total; }, 0);
  const totalPayment = rows.reduce(function (s, r) { return s + r.payment_total; }, 0);
  const totalRealisasi = rows.reduce(function (s, r) { return s + r.realisasi_total; }, 0);
  const totalSisa = rows.reduce(function (s, r) { return s + r.sisa_budget; }, 0);
  const cards = [
    ["Total Siswa Aktif", totalSiswa, ""],
    ["Total Budget", dashFmtJutaan(totalBudget), " tint-budget"],
    ["Total Klaim", dashFmtJutaan(totalPayment), " tint-klaim"],
    ["Total Realisasi", dashFmtJutaan(totalRealisasi), " tint-realisasi"],
    ["Sisa Budget", dashFmtJutaan(totalSisa), totalSisa < 0 ? " tint-negative" : ""],
  ];
  document.getElementById("dash-summary").innerHTML = cards.map(function (c) {
    return '<div class="beasiswa-dash-stat-card' + c[2] + '"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
}
```

- [ ] **Step 2: Update the skeleton loader**

In the same file, find (lines 167-172):

```javascript
function dashRenderSummarySkeleton() {
  document.getElementById("dash-summary").innerHTML = Array(5).fill(0).map(function () {
    return '<div class="budget-stat-card"><div class="label">&nbsp;</div>' +
      '<div class="fh-skel" style="width:70%;height:20px;margin-top:.25rem"></div></div>';
  }).join("");
}
```

Replace with:

```javascript
function dashRenderSummarySkeleton() {
  document.getElementById("dash-summary").innerHTML = Array(5).fill(0).map(function () {
    return '<div class="beasiswa-dash-stat-card"><div class="label">&nbsp;</div>' +
      '<div class="fh-skel" style="width:70%;height:20px;margin-top:.25rem"></div></div>';
  }).join("");
}
```

- [ ] **Step 3: Structural verification**

Run:
```bash
cd app && python3 -c "
src = open('static/js/dashboard_beasiswa.js', encoding='utf-8').read()
assert 'budget-stat-card' not in src, 'old class name still present'
assert src.count('beasiswa-dash-stat-card') == 2, 'expected exactly 2 occurrences (render + skeleton)'
assert 'tint-budget' in src and 'tint-klaim' in src and 'tint-realisasi' in src and 'tint-negative' in src
print('STRUCTURAL_OK')
"
```
Expected: `STRUCTURAL_OK`.

- [ ] **Step 4: Commit**

```bash
git add app/static/js/dashboard_beasiswa.js
git commit -m "feat: apply tint-per-semantic classes to Beasiswa Dashboard summary cards"
```

---

## Task 4: Final verification — zero blast radius + full regression

**Files:**
- None modified (verification only)

**Interfaces:**
- Consumes: everything from Tasks 1-3

- [ ] **Step 1: Confirm zero blast radius on the two other consumers**

Run:
```bash
cd /c/Financehub && git diff --stat HEAD~3 -- app/templates/sahabat_etf/index.html app/templates/budget/dashboard.html app/static/css/budget.css
```
Expected: empty output (no changes to any of these 3 files across the last 3 commits from this plan).

- [ ] **Step 2: Force-render the Beasiswa page end-to-end**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
app.config['TESTING'] = True
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess['user'] = 'test'
        sess['company_id'] = 2
        sess['role'] = 'admin'
    resp = c.get('/beasiswa/')
    print('STATUS', resp.status_code)
"
```
Expected: `STATUS 200` (if it instead redirects to login, that's the auth guard doing its job outside what a fake session can satisfy — in that case, confirm no 500/Jinja traceback appears in the output instead, which is the actual thing this check guards against).

- [ ] **Step 3: Full Python regression suite**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py tests/test_pam_remove_student.py tests/test_beasiswa_service.py tests/test_payment_memo_service.py -q`
Expected: same pass/fail counts as before this plan (no backend code changed in any of the 3 tasks) — the pre-existing `test_set_pam_complete_cascade_advance_pillar_sets_paid_not_complete` failure (and, if run against a working tree carrying the user's separate uncommitted WIP, up to 2 more bank_setf-sync failures) are expected and unrelated.

- [ ] **Step 4: Manual browser check (if a preview session is available)**

Navigate to the Beasiswa Dashboard, confirm: 5 summary cards show tint colors matching the spec's mapping (budget=blue, klaim=yellow, realisasi=green, sisa=red only if negative), the 9 chart/table cards show 3 section labels (Trend / Breakdown Realisasi / Detail Transaksi), and dark-mode toggle (if present) doesn't break the tint colors' readability. Skip this step if no preview/browser session is available in the current environment — do not block on it.
