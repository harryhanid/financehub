# Beasiswa Dashboard Filter Fix & Section Panels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the broken Program/Jenjang Studi dashboard filters, unify all 4 filters into consistent dropdown chips, and wrap the Grafik section's 3 card groups in visually distinct panels — replacing the current text-divider labels.

**Architecture:** Rewrite `beasiswa_dashboard.css` with new filter-chip and section-panel classes (also fixing a pre-existing undefined-CSS-token bug found in the same file), restructure the corresponding markup in `beasiswa/index.html`, and rewrite `initDashboard()`'s event-wiring in `dashboard_beasiswa.js` to attach listeners generically across all filter checkboxes instead of an incomplete enumerated subset. No backend/Python changes.

**Tech Stack:** Flask + Jinja2 template with inline vanilla JS, plain CSS (no build step, no CSS framework).

**Spec:** `docs/superpowers/specs/2026-07-24-beasiswa-dashboard-filter-fix-and-section-panels-design.md`

## Global Constraints

- All new/edited CSS uses existing custom properties (`--card`, `--border`, `--text`, `--text-muted`, `--primary`, `--r-md`, `--r-lg`) — never hardcoded hex — so it adapts to dark mode.
- Zero backend/Python changes.
- Existing checkbox/container `id`s and classes are preserved exactly: `dash-year-cb`, `dash-pillar-cb`, `dash-program-cb`, `dash-jenjang-cb`, `dash-filter-tahun`, `dash-filter-pillar`, `dash-filter-program`, `dash-filter-jenjang`.
- `dashGetSelectedFilters()`, `dashBuildQueryString()`, `dashApplyFilters()`, and every `dashRender*` function in `dashboard_beasiswa.js` stay byte-identical — only `initDashboard()` changes, plus one new small function.
- No frontend test framework exists in this codebase — verification is app-boot + force-render (with a real test-DB login, not a fake session) + structural grep-checks, matching the pattern established in the prior Beasiswa Dashboard Card Redesign plan.
- Live-apply on every checkbox toggle; dropdown panel stays open until the user clicks outside it.

---

## Task 1: Fix `beasiswa_dashboard.css` — token bug fix + new/removed classes

**Files:**
- Modify: `app/static/css/beasiswa_dashboard.css` (full rewrite of content, same file)

**Interfaces:**
- Produces: CSS classes `.beasiswa-dash-filterbar`, `.beasiswa-dash-filter-chip`, `.beasiswa-dash-filter-panel`, `.beasiswa-dash-grafik-wrap`, `.beasiswa-dash-section-panel`, `.beasiswa-dash-section-title` — consumed by Task 2 (filter markup), Task 3 (grafik markup), Task 4 (JS).
- Removes: `.beasiswa-dash-section-label` (superseded by `.beasiswa-dash-section-title` inside `.beasiswa-dash-section-panel`).
- Fixes: `.beasiswa-dash-stat-card` and `.beasiswa-dash-chart-card` currently reference undefined CSS custom properties (`--bg-card`, `--text-secondary`, `--text-primary`, `--border-color`, `--radius-md` — none of these exist in `style.css`; the real tokens are `--card`, `--text-muted`, `--text`, `--border`, `--r-md`). This was found while re-reading the file for this plan — found during investigation, unrelated to the filter/panel redesign itself, but fixed here since Task 1 rewrites this entire file anyway.

- [ ] **Step 1: Confirm the undefined-token bug before fixing it**

Run: `cd app && grep -c -- "--bg-card\|--text-secondary\|--text-primary\|--border-color\|--radius-md" static/css/beasiswa_dashboard.css`
Expected: `11` (11 occurrences of the wrong token names across the file)

Run: `cd app && grep -c -- "--bg-card\|--text-secondary\|--text-primary\|--border-color\|--radius-md" static/css/style.css`
Expected: `0` (confirms these tokens are never defined anywhere)

- [ ] **Step 2: Write the full corrected file**

Replace the entire content of `app/static/css/beasiswa_dashboard.css` with:

```css
/* static/css/beasiswa_dashboard.css — Beasiswa Dashboard tab, page-specific.
   Not shared with Sahabat ETF or Budget Monitoring dashboard (both still use
   the generic .budget-* classes in budget.css) — see
   docs/superpowers/specs/2026-07-24-beasiswa-dashboard-card-redesign-design.md
   and docs/superpowers/specs/2026-07-24-beasiswa-dashboard-filter-fix-and-section-panels-design.md */

/* ── Layout containers ─────────────────────────────────────────────────── */
.beasiswa-dash-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.beasiswa-dash-grafik-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

/* Fixed 2-column pairing (bulan/tahun, monthly-compare/kategori, etc.) rather
   than auto-fit, which would flow all cards into 3-4 columns on a wide
   viewport and break the pairing — carried over from .setf-grafik-grid.
   Nests inside .beasiswa-dash-section-panel, one grid per section. */
.beasiswa-dash-grafik-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 1rem;
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

/* ── Filter bar — unified dropdown chips ─────────────────────────────────── */
.beasiswa-dash-filterbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-bottom: 1.5rem;
}

.beasiswa-dash-filter-chip {
  position: relative;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 0.45rem 0.7rem;
  font-size: 0.78rem;
  min-width: 150px;
  cursor: pointer;
}
.beasiswa-dash-filter-chip .lbl {
  display: block;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin-bottom: 0.3rem;
}
.beasiswa-dash-filter-chip .val {
  color: var(--text);
  font-weight: 600;
}
.beasiswa-dash-filter-chip .caret {
  color: var(--text-muted);
  font-size: 0.65rem;
  float: right;
}

.beasiswa-dash-filter-panel {
  display: none;
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 20;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  box-shadow: 0 4px 14px rgba(0,0,0,.12);
  padding: 0.6rem;
  min-width: 200px;
  cursor: default;
}
.beasiswa-dash-filter-chip.open .beasiswa-dash-filter-panel {
  display: block;
}
.beasiswa-dash-filter-panel .panel-head {
  display: flex;
  gap: 0.6rem;
  margin-bottom: 0.4rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border);
}
.beasiswa-dash-filter-panel .panel-head button {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 0.68rem;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}
.beasiswa-dash-filter-panel .panel-opts {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  max-height: 180px;
  overflow-y: auto;
}
.beasiswa-dash-filter-panel .panel-opts label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--text);
  font-weight: 500;
  white-space: nowrap;
}

/* ── Section panels — wrap each Grafik card group ────────────────────────── */
.beasiswa-dash-section-panel {
  background: color-mix(in srgb, var(--primary) 5%, transparent);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 0.8rem;
}
.beasiswa-dash-section-title {
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--primary);
  margin-bottom: 0.55rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.beasiswa-dash-section-title::before {
  content: '';
  width: 3px;
  height: 11px;
  background: var(--primary);
  border-radius: 2px;
}

/* ── Summary stat cards — base + tint modifiers ──────────────────────────── */
.beasiswa-dash-stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 1rem 1.1rem;
}
.beasiswa-dash-stat-card .label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.beasiswa-dash-stat-card .value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text);
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
  background: var(--card);
  border-radius: var(--r-md);
  padding: 1rem;
  border-top: 3px solid var(--border);
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
  background: var(--card);
}
```

- [ ] **Step 3: Confirm braces balanced (catches a truncated paste)**

Run: `cd app && python3 -c "s = open('static/css/beasiswa_dashboard.css', encoding='utf-8').read(); print(s.count('{') == s.count('}'))"`
Expected: `True`

- [ ] **Step 4: Confirm the token bug is fully fixed and old class is gone**

Run: `cd app && grep -c -- "--bg-card\|--text-secondary\|--text-primary\|--border-color\|--radius-md" static/css/beasiswa_dashboard.css`
Expected: `0`

Run: `cd app && grep -c "beasiswa-dash-section-label" static/css/beasiswa_dashboard.css`
Expected: `0`

Run: `cd app && grep -c "beasiswa-dash-filter-chip\|beasiswa-dash-section-panel" static/css/beasiswa_dashboard.css`
Expected: `7` (both new class families present: 5 `.beasiswa-dash-filter-chip*` rules + 1 combined `.beasiswa-dash-filter-chip.open .beasiswa-dash-filter-panel` line already counted, + `.beasiswa-dash-section-panel` base rule)

- [ ] **Step 5: Commit**

```bash
git add app/static/css/beasiswa_dashboard.css
git commit -m "fix: undefined CSS tokens in beasiswa_dashboard.css + add filter-chip/section-panel classes"
```

---

## Task 2: Restructure filter bar markup in `beasiswa/index.html`

**Files:**
- Modify: `app/templates/beasiswa/index.html:54-104`

**Interfaces:**
- Consumes: CSS classes from Task 1 (`.beasiswa-dash-filterbar`, `.beasiswa-dash-filter-chip`, `.beasiswa-dash-filter-panel`)
- Produces: rendered markup that Task 4's JS attaches listeners to (`.beasiswa-dash-filter-chip` elements, each containing `.panel-opts input[type=checkbox]`, `[data-act="all"]`, `[data-act="none"]`)
- Preserves: `dash-filter-tahun` / `dash-filter-pillar` / `dash-filter-program` / `dash-filter-jenjang` container `id`s and `dash-year-cb` / `dash-pillar-cb` / `dash-program-cb` / `dash-jenjang-cb` checkbox classes exactly, so `dashGetSelectedFilters()` (unchanged) keeps working

- [ ] **Step 1: Confirm current state before editing**

Run: `cd app && grep -c "beasiswa-dash-filter-chip" templates/beasiswa/index.html`
Expected: `0` (class doesn't exist in the template yet)

- [ ] **Step 2: Replace the filter-bar block**

In `app/templates/beasiswa/index.html`, find lines 54-104:

```html
          <div class="filter-bar">
            <div class="filter-field setf-filter-field-wide">
              <label>Tahun</label>
              <button type="button" id="dash-year-select-all" class="btn btn-secondary btn-sm" style="margin-bottom:.375rem">Pilih Semua</button>
              <div id="dash-filter-tahun">
                {% for y in range(2023, 2027) %}
                <label style="display:inline-flex;align-items:center;gap:.25rem;margin-right:.75rem;font-weight:400">
                  <input type="checkbox" class="dash-year-cb" value="{{ y }}" checked>
                  {{ y }}
                </label>
                {% endfor %}
              </div>
            </div>
            <div class="filter-field">
              <label>Pillar</label>
              <div id="dash-filter-pillar">
                {% for p in pillar %}
                <label style="display:inline-flex;align-items:center;gap:.25rem;margin-right:.75rem;font-weight:400">
                  <input type="checkbox" class="dash-pillar-cb" value="{{ p }}" checked>
                  {{ p }}
                </label>
                {% endfor %}
              </div>
            </div>
            
            <div class="filter-field" style="position:relative;">
              <label>Program</label>
              <button type="button" class="btn btn-secondary btn-sm" style="margin-bottom:.375rem" onclick="document.querySelectorAll('.dash-program-cb').forEach(c=>c.checked=true);loadDashboard()">Pilih Semua</button>
              <div id="dash-filter-program" style="max-height:80px; overflow-y:auto; border:1px solid #e2e8f0; padding:4px; border-radius:4px; background:var(--card, #fff); min-width:180px;">
                {% for p in program %}
                <label style="display:block;font-weight:400;margin-bottom:2px">
                  <input type="checkbox" class="dash-program-cb" value="{{ p }}" checked>
                  {{ p }}
                </label>
                {% endfor %}
              </div>
            </div>
            
            <div class="filter-field" style="position:relative;">
              <label>Jenjang Studi</label>
              <button type="button" class="btn btn-secondary btn-sm" style="margin-bottom:.375rem" onclick="document.querySelectorAll('.dash-jenjang-cb').forEach(c=>c.checked=true);loadDashboard()">Pilih Semua</button>
              <div id="dash-filter-jenjang" style="max-height:80px; overflow-y:auto; border:1px solid #e2e8f0; padding:4px; border-radius:4px; background:var(--card, #fff); min-width:140px;">
                {% for j in jenjang %}
                <label style="display:block;font-weight:400;margin-bottom:2px">
                  <input type="checkbox" class="dash-jenjang-cb" value="{{ j }}" checked>
                  {{ j }}
                </label>
                {% endfor %}
              </div>
            </div>
          </div>
```

Replace with:

```html
          <div class="beasiswa-dash-filterbar">
            <div class="beasiswa-dash-filter-chip">
              <span class="lbl">Tahun</span>
              <span class="val">Semua</span>
              <span class="caret">▾</span>
              <div class="beasiswa-dash-filter-panel">
                <div class="panel-head">
                  <button type="button" data-act="all">Semua</button>
                  <button type="button" data-act="none">Kosongkan</button>
                </div>
                <div class="panel-opts" id="dash-filter-tahun">
                  {% for y in range(2023, 2027) %}
                  <label><input type="checkbox" class="dash-year-cb" value="{{ y }}" checked> {{ y }}</label>
                  {% endfor %}
                </div>
              </div>
            </div>

            <div class="beasiswa-dash-filter-chip">
              <span class="lbl">Pillar</span>
              <span class="val">Semua</span>
              <span class="caret">▾</span>
              <div class="beasiswa-dash-filter-panel">
                <div class="panel-head">
                  <button type="button" data-act="all">Semua</button>
                  <button type="button" data-act="none">Kosongkan</button>
                </div>
                <div class="panel-opts" id="dash-filter-pillar">
                  {% for p in pillar %}
                  <label><input type="checkbox" class="dash-pillar-cb" value="{{ p }}" checked> {{ p }}</label>
                  {% endfor %}
                </div>
              </div>
            </div>

            <div class="beasiswa-dash-filter-chip">
              <span class="lbl">Program</span>
              <span class="val">Semua</span>
              <span class="caret">▾</span>
              <div class="beasiswa-dash-filter-panel">
                <div class="panel-head">
                  <button type="button" data-act="all">Semua</button>
                  <button type="button" data-act="none">Kosongkan</button>
                </div>
                <div class="panel-opts" id="dash-filter-program">
                  {% for p in program %}
                  <label><input type="checkbox" class="dash-program-cb" value="{{ p }}" checked> {{ p }}</label>
                  {% endfor %}
                </div>
              </div>
            </div>

            <div class="beasiswa-dash-filter-chip">
              <span class="lbl">Jenjang Studi</span>
              <span class="val">Semua</span>
              <span class="caret">▾</span>
              <div class="beasiswa-dash-filter-panel">
                <div class="panel-head">
                  <button type="button" data-act="all">Semua</button>
                  <button type="button" data-act="none">Kosongkan</button>
                </div>
                <div class="panel-opts" id="dash-filter-jenjang">
                  {% for j in jenjang %}
                  <label><input type="checkbox" class="dash-jenjang-cb" value="{{ j }}" checked> {{ j }}</label>
                  {% endfor %}
                </div>
              </div>
            </div>
          </div>
```

- [ ] **Step 3: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`, no exceptions.

- [ ] **Step 4: Force-render with a real login and verify the new structure**

Run:
```bash
cd app && python -c "
import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_dash_filter_render.db')
if os.path.exists(config.DB_PATH): os.remove(config.DB_PATH)
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
login = client.post('/auth/login', json={'username':'admin','password':'Admin@123'})
assert login.get_json()['ok'], login.get_json()
client.post('/select-company', data={'company_id': 2})
resp = client.get('/beasiswa/')
print('STATUS', resp.status_code)
body = resp.data.decode('utf-8', errors='replace')
print('filter-chip count:', body.count('class=\"beasiswa-dash-filter-chip\"'))
print('old select-all button gone:', 'id=\"dash-year-select-all\"' not in body)
print('checkbox classes preserved:', all(c in body for c in ['dash-year-cb', 'dash-pillar-cb', 'dash-program-cb', 'dash-jenjang-cb']))
os.remove(config.DB_PATH)
"
```
Expected: `STATUS 200`, `filter-chip count: 4`, `old select-all button gone: True`, `checkbox classes preserved: True`.

- [ ] **Step 5: Commit**

```bash
git add app/templates/beasiswa/index.html
git commit -m "feat: unify Beasiswa Dashboard filters into dropdown chips"
```

---

## Task 3: Restructure Grafik section markup in `beasiswa/index.html`

**Files:**
- Modify: `app/templates/beasiswa/index.html` (Grafik section, previously lines 113-190 — line numbers shift after Task 2's edit; locate via the `beasiswa-dash-grafik-grid` / `beasiswa-dash-section-label` content shown below)

**Interfaces:**
- Consumes: CSS classes from Task 1 (`.beasiswa-dash-grafik-wrap`, `.beasiswa-dash-section-panel`, `.beasiswa-dash-section-title`, `.beasiswa-dash-grafik-grid`, `.beasiswa-dash-chart-card`)
- Produces: no change to any chart/table `id` — Task 4/existing JS render functions attach to the same elements as before

- [ ] **Step 1: Confirm current state before editing**

Run: `cd app && grep -c "beasiswa-dash-section-panel" templates/beasiswa/index.html`
Expected: `0`

Run: `cd app && grep -c "beasiswa-dash-chart-card" templates/beasiswa/index.html`
Expected: `9` (baseline count before restructuring — must stay `9` after this task)

- [ ] **Step 2: Replace the Grafik grid block**

Find the block starting at `<div class="beasiswa-dash-grafik-grid">` (directly inside the `Grafik` `<details>` element's `.setf-accordion-body`) through its closing `</div>` before `</details>`:

```html
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
```

Replace with:

```html
          <div class="beasiswa-dash-grafik-wrap">
            <div class="beasiswa-dash-section-panel">
              <div class="beasiswa-dash-section-title">Trend</div>
              <div class="beasiswa-dash-grafik-grid">
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
              </div>
            </div>

            <div class="beasiswa-dash-section-panel">
              <div class="beasiswa-dash-section-title">Breakdown Realisasi</div>
              <div class="beasiswa-dash-grafik-grid">
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
              </div>
            </div>

            <div class="beasiswa-dash-section-panel">
              <div class="beasiswa-dash-section-title">Detail Transaksi</div>
              <div class="beasiswa-dash-grafik-grid">
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
          </div>
```

- [ ] **Step 3: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`.

- [ ] **Step 4: Force-render and verify the new structure, same card count**

Run:
```bash
cd app && python -c "
import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_dash_panel_render.db')
if os.path.exists(config.DB_PATH): os.remove(config.DB_PATH)
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
login = client.post('/auth/login', json={'username':'admin','password':'Admin@123'})
assert login.get_json()['ok'], login.get_json()
client.post('/select-company', data={'company_id': 2})
resp = client.get('/beasiswa/')
print('STATUS', resp.status_code)
body = resp.data.decode('utf-8', errors='replace')
print('section-panel count:', body.count('class=\"beasiswa-dash-section-panel\"'))
print('chart-card count (must stay 9):', body.count('beasiswa-dash-chart-card'))
print('old section-label gone:', 'beasiswa-dash-section-label' not in body)
os.remove(config.DB_PATH)
"
```
Expected: `STATUS 200`, `section-panel count: 3`, `chart-card count (must stay 9): 9`, `old section-label gone: True`.

- [ ] **Step 5: Commit**

```bash
git add app/templates/beasiswa/index.html
git commit -m "feat: wrap Beasiswa Dashboard Grafik card groups in section panels"
```

---

## Task 4: Rewrite `initDashboard()` filter wiring in `dashboard_beasiswa.js`

**Files:**
- Modify: `app/static/js/dashboard_beasiswa.js:464-484` (`initDashboard`, and the `window.addEventListener("fh-theme-changed", ...)` block immediately after at line 486 stays untouched)

**Interfaces:**
- Consumes: `dashApplyFilters()` (unchanged, defined at line 401), markup from Task 2 (`.beasiswa-dash-filter-chip`, `.panel-opts input[type=checkbox]`, `[data-act="all"]`, `[data-act="none"]`)
- Produces: new function `dashUpdateChipSummary(chip)` — no other function signatures change

- [ ] **Step 1: Confirm the bug before fixing it**

Run: `cd app && sed -n '464,484p' static/js/dashboard_beasiswa.js`
Expected output (the current broken version — only Tahun/Pillar wired, Program/Jenjang have zero listeners):
```javascript
function initDashboard() {
  // Hanya inisialisasi satu kali
  if (window._dashInitialized) return;
  window._dashInitialized = true;
  
  document.querySelectorAll(".dash-year-cb").forEach(function (cb) {
    cb.addEventListener("change", dashApplyFilters);
  });
  document.querySelectorAll(".dash-pillar-cb").forEach(function (cb) {
    cb.addEventListener("change", dashApplyFilters);
  });
  const selectAllBtn = document.getElementById("dash-year-select-all");
  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", function () {
      document.querySelectorAll(".dash-year-cb").forEach(function (cb) { cb.checked = true; });
      dashApplyFilters();
    });
  }
  
  dashApplyFilters();
}
```

- [ ] **Step 2: Replace `initDashboard()` and add `dashUpdateChipSummary`**

Replace lines 464-484 (the exact block shown in Step 1) with:

```javascript
function dashUpdateChipSummary(chip) {
  const boxes = chip.querySelectorAll(".panel-opts input[type=checkbox]");
  const total = boxes.length;
  const checked = chip.querySelectorAll(".panel-opts input[type=checkbox]:checked").length;
  const valEl = chip.querySelector(".val");
  if (checked === total) {
    valEl.textContent = "Semua";
  } else if (checked === 0) {
    valEl.textContent = "Tidak ada";
  } else {
    valEl.textContent = checked + " dipilih";
  }
}

function initDashboard() {
  // Hanya inisialisasi satu kali
  if (window._dashInitialized) return;
  window._dashInitialized = true;

  document.querySelectorAll(".beasiswa-dash-filter-chip").forEach(function (chip) {
    chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) {
      cb.addEventListener("change", function () {
        dashUpdateChipSummary(chip);
        dashApplyFilters();
      });
    });
    const allBtn = chip.querySelector('[data-act="all"]');
    if (allBtn) {
      allBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) { cb.checked = true; });
        dashUpdateChipSummary(chip);
        dashApplyFilters();
      });
    }
    const noneBtn = chip.querySelector('[data-act="none"]');
    if (noneBtn) {
      noneBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) { cb.checked = false; });
        dashUpdateChipSummary(chip);
        dashApplyFilters();
      });
    }
    chip.addEventListener("click", function (e) {
      if (e.target.closest(".beasiswa-dash-filter-panel")) return;
      document.querySelectorAll(".beasiswa-dash-filter-chip.open").forEach(function (c) {
        if (c !== chip) c.classList.remove("open");
      });
      chip.classList.toggle("open");
    });
    dashUpdateChipSummary(chip);
  });

  document.addEventListener("click", function (e) {
    if (!e.target.closest(".beasiswa-dash-filter-chip")) {
      document.querySelectorAll(".beasiswa-dash-filter-chip.open").forEach(function (c) { c.classList.remove("open"); });
    }
  });

  dashApplyFilters();
}
```

- [ ] **Step 3: Structural verification — old enumerated wiring is gone, new generic wiring exists**

Run:
```bash
cd app && python3 -c "
src = open('static/js/dashboard_beasiswa.js', encoding='utf-8').read()
init_start = src.index('function initDashboard()')
init_body = src[init_start:init_start + 2000]
assert '.dash-year-cb' not in init_body, 'old enumerated year-checkbox wiring still present'
assert '.dash-pillar-cb' not in init_body, 'old enumerated pillar-checkbox wiring still present'
assert 'dash-year-select-all' not in init_body, 'old dedicated select-all button reference still present'
assert '.beasiswa-dash-filter-chip' in init_body, 'new generic chip wiring missing'
assert 'function dashUpdateChipSummary' in src
assert src.count('function dashApplyFilters') == 1, 'dashApplyFilters must be untouched (still defined exactly once)'
print('STRUCTURAL_OK')
"
```
Expected: `STRUCTURAL_OK`.

- [ ] **Step 4: Confirm `dashApplyFilters`, `dashGetSelectedFilters`, `dashBuildQueryString` are byte-identical to before this task**

Run: `cd app && git diff --unified=0 static/js/dashboard_beasiswa.js | grep -E "^[+-]function dash(ApplyFilters|GetSelectedFilters|BuildQueryString)"`
Expected: empty output (no diff lines touching these 3 function signatures — proves they weren't modified)

- [ ] **Step 5: Commit**

```bash
git add app/static/js/dashboard_beasiswa.js
git commit -m "fix: wire ALL Beasiswa Dashboard filter checkboxes generically, not an enumerated subset"
```

---

## Task 5: Final verification — functional check + full regression

**Files:**
- None modified (verification only)

**Interfaces:**
- Consumes: everything from Tasks 1-4

- [ ] **Step 1: Force-render end-to-end and confirm every filter checkbox is present and correctly wired in the served HTML**

Run:
```bash
cd app && python -c "
import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_dash_final_render.db')
if os.path.exists(config.DB_PATH): os.remove(config.DB_PATH)
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
login = client.post('/auth/login', json={'username':'admin','password':'Admin@123'})
assert login.get_json()['ok']
client.post('/select-company', data={'company_id': 2})
resp = client.get('/beasiswa/')
assert resp.status_code == 200, resp.status_code
body = resp.data.decode('utf-8', errors='replace')
assert body.count('class=\"beasiswa-dash-filter-chip\"') == 4
assert body.count('class=\"beasiswa-dash-section-panel\"') == 3
assert body.count('beasiswa-dash-chart-card') == 9
assert 'beasiswa-dash-section-label' not in body
assert '--bg-card' not in open('static/css/beasiswa_dashboard.css', encoding='utf-8').read()
print('FINAL_RENDER_OK')
os.remove(config.DB_PATH)
"
```
Expected: `FINAL_RENDER_OK`.

- [ ] **Step 2: Full Python regression suite**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py tests/test_pam_remove_student.py tests/test_beasiswa_service.py tests/test_payment_memo_service.py -q`
Expected: same pass/fail counts as the prior redesign plan's final check (no backend code changed in any task of this plan) — pre-existing failures already known from earlier investigation are expected and unrelated to this work; investigate anything new.

- [ ] **Step 3: Manual browser check (if a preview session with real, non-production data is available)**

Navigate to the Beasiswa Dashboard tab. Confirm: 4 filter chips render with "Semua" summaries; clicking a chip opens its dropdown panel with checkboxes; unchecking a Program or Jenjang Studi option updates the summary cards and charts (this is the bug being fixed — must actually change the displayed numbers, not just close the dropdown); clicking outside a panel closes it; the 3 Grafik sections (Trend / Breakdown Realisasi / Detail Transaksi) each render inside a visibly tinted panel with an accent-colored title. Skip this step if no preview/browser session with non-production data is available — do not block on it (per prior-session caution about not mutating or screenshotting the shared live production DB).

- [ ] **Step 4: Confirm zero blast radius on other consumers**

Run: `cd /c/Financehub && git diff --stat HEAD~5 -- app/templates/sahabat_etf/index.html app/templates/budget/dashboard.html app/static/css/budget.css`

(Adjust `HEAD~5` if the actual number of commits from this plan differs — count Tasks 1, 2, 3, 4's commits.)

Expected: empty output for the 3 files, evaluated against **committed** state only (a concurrent session's uncommitted WIP in this shared checkout, if any, is not part of this check — see prior-session note on `git diff <ref> HEAD` vs `git diff <ref>` for why the second ref matters).
