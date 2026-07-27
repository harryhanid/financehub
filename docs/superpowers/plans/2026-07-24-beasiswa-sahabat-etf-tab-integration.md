# Sahabat ETF Tab Integration into Beasiswa Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the "Sahabat ETF" entry in the Beasiswa page's tab bar behave like the other 6 tabs (Dashboard, Data Siswa, Data Budget, Data Payment, Report Siswa, Rekam Medis) — a real `.tab-panel` on the same page, no full page reload — instead of a hyperlink that navigates to a separate standalone page.

**Architecture:** Extract Sahabat ETF's page content into a Jinja partial, server-render it inline as a 7th `.tab-panel` in `beasiswa/index.html` (same pattern every other tab already uses — HTML shell at page load, data lazy-fetched via JS on first click), redirect the old standalone URL to the new tab, and extend the shared `initTabs()` helper to support deep-linking via a `?tab=` query parameter.

**Tech Stack:** Flask + Jinja2 templates with inline vanilla JS, no build step, no frontend test framework.

**Spec:** `docs/superpowers/specs/2026-07-24-beasiswa-sahabat-etf-tab-integration-design.md`

## Global Constraints

- Non-ETF company sessions: the Sahabat ETF tab stays visible in the tab bar; its panel shows the existing "Ganti Company" notice instead of dashboard content — no conditional tab-hiding.
- `/beasiswa/sahabat` (bare root) redirects (302) to `/beasiswa/?tab=sahabat`. All `/beasiswa/sahabat/api/*` and `/beasiswa/sahabat/export/*` routes are untouched.
- `etf_company_required` guard on the API/export routes is untouched — stays as backend defense-in-depth.
- The `initTabs()` change in `static/js/app.js` must be backward-compatible: when no `?tab=` query param is present (or it doesn't match any `data-tab`), behavior is identical to today (click the first tab). Confirmed zero collision with the 2 other `[data-tabs]`-wrapped pages (`bank/index.html`, `payment_memo/index.html`) and with `etf_payment_application/index.html`'s own unrelated `?tab=` usage (that page doesn't use `[data-tabs]`).
- No frontend test framework exists in this codebase — verification is app-boot + force-render (with a real test-DB login) + structural grep-checks, matching the pattern established in prior Beasiswa Dashboard work.
- The pre-existing duplicate-id bug (`chart-keluarga` / `setf-family-table` each appear twice in the Sahabat ETF content — once in its "Grafik" section, once in its "Detail Tabel" section) is carried over unchanged by this plan — out of scope, not to be fixed here.

---

## Task 1: Extract Sahabat ETF content into a reusable partial

**Files:**
- Create: `app/templates/sahabat_etf/_panel.html`
- Modify: `app/templates/sahabat_etf/index.html` (full rewrite — becomes a thin wrapper)

**Interfaces:**
- Produces: `sahabat_etf/_panel.html`, a Jinja partial expecting the same context variables the standalone page already receives (`wrong_company`, `available_years`, `available_pillars`) — consumed by this task's own rewritten `sahabat_etf/index.html` AND by Task 3's `beasiswa/index.html` embed.

- [ ] **Step 1: Confirm current file content before extracting**

Run: `cd app && wc -l templates/sahabat_etf/index.html`
Expected: `183 templates/sahabat_etf/index.html` (if the count differs, stop and re-read the file — the extraction boundaries below assume this exact content)

- [ ] **Step 2: Create the partial with the extracted content**

Create `app/templates/sahabat_etf/_panel.html` with this exact content (this is current lines 9–175 of `sahabat_etf/index.html`, copied verbatim — the `<div class="budget-page">...</div>` block, no changes):

```html
<div class="budget-page">
  <div class="setf-print-header">Disajikan dalam jutaan Rupiah</div>
  <h1>Dashboard Sahabat ETF</h1>

  {% if wrong_company %}
  <div class="budget-card">
    <h3>Program khusus Eka Tjipta Foundation</h3>
    <p>Halaman ini hanya menampilkan data untuk company ETF. Company aktif Anda saat ini bukan ETF.</p>
    <a class="budget-btn" href="{{ url_for('dashboard.select_company') }}">Ganti Company</a>
  </div>
  {% else %}

  <p style="color:var(--text-muted);font-size:.8rem;margin-bottom:1rem">
    Semua nilai pada dashboard ini ditampilkan dalam jutaan rupiah (Jt).
  </p>

  <details class="setf-accordion" open>
    <summary>Ringkasan &amp; Alert</summary>
    <div class="setf-accordion-body">
      <div class="filter-bar">
        <div class="filter-field setf-filter-field-wide">
          <label>Tahun</label>
          <button type="button" id="setf-year-select-all" class="btn btn-secondary btn-sm" style="margin-bottom:.375rem">Pilih Semua</button>
          <div id="setf-filter-tahun">
            {% for y in available_years %}
            <label style="display:inline-flex;align-items:center;gap:.25rem;margin-right:.75rem;font-weight:400">
              <input type="checkbox" class="setf-year-cb" value="{{ y }}" checked>
              {{ y }}
            </label>
            {% endfor %}
          </div>
        </div>
        <div class="filter-field">
          <label>Pillar</label>
          <div id="setf-filter-pillar">
            {% for p in available_pillars %}
            <label style="display:inline-flex;align-items:center;gap:.25rem;margin-right:.75rem;font-weight:400">
              <input type="checkbox" class="setf-pillar-cb" value="{{ p }}" checked>
              {{ p }}
            </label>
            {% endfor %}
          </div>
        </div>
        <div class="filter-field">
          <label>Tahun Report (Export Laporan)</label>
          <select id="setf-report-year">
            {% for y in available_years|reverse %}
            <option value="{{ y }}">{{ y }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <div class="budget-toolbar">
        <a class="budget-btn" id="setf-export-summary" href="{{ url_for('sahabat_etf.export_summary') }}">Export Ringkasan (CSV)</a>
        <a class="budget-btn" id="setf-export-detail" href="{{ url_for('sahabat_etf.export_detail') }}">Export Detail Transaksi (CSV)</a>
        <button type="button" class="budget-btn" id="setf-export-pdf" onclick="setfExportPdf()">Export PDF (Print)</button>
        <a class="budget-btn" id="setf-export-report" href="{{ url_for('sahabat_etf.export_report', year=available_years|first or 2026) }}">Export Laporan (Excel)</a>
      </div>

      <div class="budget-summary-grid" id="setf-summary"></div>

      <div class="budget-card" id="setf-alert-card" style="display:none">
        <h3>Anggota Over-Budget</h3>
        <ul id="setf-alert-list"></ul>
      </div>
    </div>
  </details>

  <details class="setf-accordion" id="setf-grafik-accordion" open>
    <summary>Grafik</summary>
    <div class="setf-accordion-body">
      <div class="setf-grafik-grid">
        <div class="budget-chart-card"><h3>Trend per Bulan</h3><canvas id="chart-bulanan"></canvas></div>
        <div class="budget-chart-card"><h3>Trend per Tahun</h3><canvas id="chart-tahunan"></canvas></div>

        <div class="budget-chart-card setf-compact-card">
          <h3>Perbandingan Realisasi per Bulan per Tahun</h3>
          <div class="setf-compact-scroll">
            <table id="setf-monthly-table">
              <thead><tr id="setf-monthly-thead-row"><th>Bulan</th></tr></thead>
              <tbody><tr><td style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
            </table>
          </div>
        </div>
        <div class="budget-chart-card setf-compact-card">
          <h3>Realisasi per Pillar</h3>
          <div class="setf-compact-scroll">
            <table id="setf-pillar-table">
              <thead><tr><th>Pillar</th><th>Budget</th><th>Realisasi</th><th>Sisa</th></tr></thead>
              <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
            </table>
          </div>
        </div>

        <div class="budget-chart-card"><h3>Realisasi per Keluarga</h3><canvas id="chart-keluarga"></canvas></div>
        <div class="budget-chart-card setf-compact-card">
          <h3>Realisasi per Keluarga (Tabel)</h3>
          <div class="setf-compact-scroll">
            <table id="setf-family-table">
              <thead><tr><th>Keluarga</th><th>Nama</th><th>Kategori Realisasi</th><th class="num-right">Realisasi</th></tr></thead>
              <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
            </table>
          </div>
        </div>

        <div class="budget-chart-card"><h3>Realisasi per Kategori</h3><canvas id="chart-kategori"></canvas></div>
        <div class="budget-chart-card setf-compact-card">
          <h3>Realisasi per Kategori (Tabel)</h3>
          <div class="setf-compact-scroll">
            <table id="setf-kategori-table">
              <thead><tr><th>Kategori</th><th>Budget</th><th>Realisasi</th><th>Sisa</th></tr></thead>
              <tbody><tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
            </table>
          </div>
        </div>

        <div class="budget-chart-card setf-compact-card" style="grid-column:1/3">
          <h3>10 Transaksi Terakhir</h3>
          <div id="setf-drilldown-chip" class="setf-drilldown-chip" style="display:none"></div>
          <div class="setf-compact-scroll">
            <table id="setf-latest-payments-table">
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
      </div>
    </div>
  </details>

  <details class="setf-accordion" id="setf-detail-tabel" open>
    <summary>Detail Tabel</summary>
    <div class="setf-accordion-body">
      <div class="table-wrap">
        <h3>Realisasi per Keluarga</h3>
        <canvas id="chart-keluarga"></canvas>
        <div class="setf-compact-scroll">
          <table id="setf-family-table">
            <thead><tr><th>Keluarga</th><th>Nama</th><th class="num-right">Realisasi</th></tr></thead>
            <tbody><tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
          </table>
        </div>
      </div>

      <div class="table-wrap">
        <h3>Rincian Budget vs Realisasi per Anggota</h3>
        <table id="setf-table">
          <thead>
            <tr><th>Nama</th><th>Jenjang</th><th>Angkatan</th><th>Status</th>
                <th>Budget</th><th>Klaim</th><th>Realisasi</th><th>Sisa</th></tr>
          </thead>
          <tbody><tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
        </table>
      </div>
    </div>
  </details>
  {% endif %}
</div>
```

- [ ] **Step 3: Rewrite `sahabat_etf/index.html` as a thin wrapper**

Replace the entire content of `app/templates/sahabat_etf/index.html` with:

```html
{% extends "base.html" %}
{% block title %}Sahabat ETF{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/budget.css') }}">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
{% endblock %}
{% block content %}
{% include "sahabat_etf/_panel.html" %}
{% endblock %}
{% block scripts %}
<script src="{{ url_for('static', filename='js/sahabat_etf.js') }}"></script>
{% if not wrong_company %}
<script>document.addEventListener("DOMContentLoaded", initSahabatEtf);</script>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`.

- [ ] **Step 5: Force-render the standalone page still works unchanged**

Run:
```bash
cd app && python -c "
import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_setf_standalone_render.db')
if os.path.exists(config.DB_PATH): os.remove(config.DB_PATH)
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
login = client.post('/auth/login', json={'username':'admin','password':'Admin@123'})
assert login.get_json()['ok']
client.post('/select-company', data={'company_id': 2})
resp = client.get('/beasiswa/sahabat/')
print('STATUS', resp.status_code)
body = resp.data.decode('utf-8', errors='replace')
print('has setf-summary:', 'id=\"setf-summary\"' in body)
os.remove(config.DB_PATH)
"
```
Expected: `STATUS 200`, `has setf-summary: True` (company_id=2 is ETF per existing test fixtures used throughout this codebase's other tests — confirms the extraction didn't break the standalone page).

- [ ] **Step 6: Commit**

```bash
git add app/templates/sahabat_etf/_panel.html app/templates/sahabat_etf/index.html
git commit -m "refactor: extract Sahabat ETF content into a reusable Jinja partial"
```

---

## Task 2: Pass Sahabat ETF context variables from the Beasiswa route

**Files:**
- Modify: `app/modules/beasiswa/routes.py:1-61`

**Interfaces:**
- Consumes: `modules.sahabat_etf.service.get_available_years(company_id)`, `modules.sahabat_etf.service.get_available_pillars(company_id)` (both already exist, unchanged)
- Produces: `beasiswa/index.html`'s render context now includes `wrong_company`, `available_years`, `available_pillars` — consumed by Task 3's embedded partial

- [ ] **Step 1: Confirm current route content**

Run: `cd app && sed -n '1,61p' modules/beasiswa/routes.py`
Expected: matches the current imports (lines 1-17) and `index()` function (lines 41-61) — if it doesn't match, stop and re-read before editing (another concurrent session may have changed this file; do not overwrite unrelated changes — see the shared-checkout caution in your dispatch).

- [ ] **Step 2: Add the import**

In `app/modules/beasiswa/routes.py`, find (line 17-18):

```python
    get_dashboard_latest_payments, get_dashboard_program_summary, get_dashboard_pillar_yearly,
)
import config
```

Replace with:

```python
    get_dashboard_latest_payments, get_dashboard_program_summary, get_dashboard_pillar_yearly,
)
from modules.sahabat_etf.service import get_available_years, get_available_pillars
import config
```

- [ ] **Step 3: Add the context variables to `index()`**

Find (lines 41-61):

```python
@bp.route("/")
@jwt_html_required
def index():
    if not _cid():
        return redirect(url_for("dashboard.select_company"))
    return render_template(
        "beasiswa/index.html",
        siswa_list=get_siswa_list(_cid()),
        jenjang=config.JENJANG,
        program=config.PROGRAM,
        status_siswa=config.STATUS_SISWA,
        pillar=config.PILLAR,
        cat1_bgt=config.CAT1_BGT,
        cat2_sem=config.CAT2_SEM,
        perusahaan=config.PERUSAHAAN,
        vendor_list=get_vendors(),
        universitas_list=get_distinct_universitas(_cid()),
        cat3_medical=config.CAT3_MEDICAL,
        active_page="beasiswa",
        **_ctx()
    )
```

Replace with:

```python
@bp.route("/")
@jwt_html_required
def index():
    if not _cid():
        return redirect(url_for("dashboard.select_company"))
    return render_template(
        "beasiswa/index.html",
        siswa_list=get_siswa_list(_cid()),
        jenjang=config.JENJANG,
        program=config.PROGRAM,
        status_siswa=config.STATUS_SISWA,
        pillar=config.PILLAR,
        cat1_bgt=config.CAT1_BGT,
        cat2_sem=config.CAT2_SEM,
        perusahaan=config.PERUSAHAAN,
        vendor_list=get_vendors(),
        universitas_list=get_distinct_universitas(_cid()),
        cat3_medical=config.CAT3_MEDICAL,
        active_page="beasiswa",
        wrong_company=(session.get("company_code") != "ETF"),
        available_years=get_available_years(_cid()),
        available_pillars=get_available_pillars(_cid()),
        **_ctx()
    )
```

- [ ] **Step 4: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK` (this catches an import error — e.g. a circular import between `modules.beasiswa.routes` and `modules.sahabat_etf.service` — immediately).

- [ ] **Step 5: Commit**

```bash
git add app/modules/beasiswa/routes.py
git commit -m "feat: pass Sahabat ETF context variables from the Beasiswa index route"
```

---

## Task 3: Embed Sahabat ETF as the 7th tab in `beasiswa/index.html`

**Files:**
- Modify: `app/templates/beasiswa/index.html:20-28` (tab bar)
- Modify: `app/templates/beasiswa/index.html:617-619` (new tab-panel, inserted between the `tab-rekam` panel's close and the `data-tabs` wrapper's close)
- Modify: `app/templates/beasiswa/index.html:880-881` (scripts block)

**Interfaces:**
- Consumes: `sahabat_etf/_panel.html` (Task 1), `wrong_company`/`available_years`/`available_pillars` context (Task 2), `initSahabatEtf()` (exists today in `static/js/sahabat_etf.js`, gets its idempotency guard in Task 5)
- Produces: a `data-tab="tab-sahabat"` button and `id="tab-sahabat"` panel that Task 6's `initTabs()` deep-link logic and Task 4's redirect both target by the literal string `sahabat`

- [ ] **Step 1: Confirm current tab bar content**

Run: `cd app && sed -n '20,28p' templates/beasiswa/index.html`
Expected:
```html
    <div class="tabs" style="margin-bottom:0" title="Alt+&#8592; / Alt+&#8594; untuk pindah tab">
      <button class="tab-btn" data-tab="tab-dashboard" onclick="loadDashboard()">Dashboard</button>
      <button class="tab-btn" data-tab="tab-siswa" onclick="loadRekap()">Data Siswa</button>
      <button class="tab-btn" data-tab="tab-budget" onclick="loadBudgetList()">Data Budget</button>
      <button class="tab-btn" data-tab="tab-payment" onclick="loadPaymentList()">Data Payment</button>
      <button class="tab-btn" data-tab="tab-laporan" onclick="lprReset()">Report Siswa</button>
      <button class="tab-btn" data-tab="tab-rekam" onclick="loadRekamMedis()">Rekam Medis</button>
    </div>
    <a class="tab-btn" href="/beasiswa/sahabat" style="text-decoration:none;display:inline-flex;align-items:center">Sahabat ETF ↗</a>
```
If it doesn't match exactly, stop and re-locate the block before editing (line numbers may have shifted from other uncommitted work in this shared checkout).

- [ ] **Step 2: Move Sahabat ETF into the tab bar**

Replace the block from Step 1 with:

```html
    <div class="tabs" style="margin-bottom:0" title="Alt+&#8592; / Alt+&#8594; untuk pindah tab">
      <button class="tab-btn" data-tab="tab-dashboard" onclick="loadDashboard()">Dashboard</button>
      <button class="tab-btn" data-tab="tab-siswa" onclick="loadRekap()">Data Siswa</button>
      <button class="tab-btn" data-tab="tab-budget" onclick="loadBudgetList()">Data Budget</button>
      <button class="tab-btn" data-tab="tab-payment" onclick="loadPaymentList()">Data Payment</button>
      <button class="tab-btn" data-tab="tab-laporan" onclick="lprReset()">Report Siswa</button>
      <button class="tab-btn" data-tab="tab-rekam" onclick="loadRekamMedis()">Rekam Medis</button>
      <button class="tab-btn" data-tab="tab-sahabat" onclick="initSahabatEtf()">Sahabat ETF</button>
    </div>
```

- [ ] **Step 3: Confirm current end-of-tabs boundary**

Run: `cd app && sed -n '615,620p' templates/beasiswa/index.html`
Expected:
```html
      </div>
    </div>
  </div>

</div>

```
(three closing `</div>` — end of `tab-rekam`'s inner content, end of `tab-rekam` panel, and the blank line before `</div>` closing `data-tabs`.)

- [ ] **Step 4: Insert the new tab-panel**

Find (the exact lines from Step 3):

```html
      </div>
    </div>
  </div>

</div>
```

Replace with:

```html
      </div>
    </div>
  </div>

  <div class="tab-panel" id="tab-sahabat">
    {% include "sahabat_etf/_panel.html" %}
  </div>

</div>
```

- [ ] **Step 5: Confirm current scripts-block start**

Run: `cd app && sed -n '880,882p' templates/beasiswa/index.html`
Expected:
```html
{% block scripts %}
<script src="{{ url_for('static', filename='js/dashboard_beasiswa.js') }}"></script>
<script>
```

- [ ] **Step 6: Add the Sahabat ETF JS file**

Find:

```html
{% block scripts %}
<script src="{{ url_for('static', filename='js/dashboard_beasiswa.js') }}"></script>
<script>
```

Replace with:

```html
{% block scripts %}
<script src="{{ url_for('static', filename='js/dashboard_beasiswa.js') }}"></script>
<script src="{{ url_for('static', filename='js/sahabat_etf.js') }}"></script>
<script>
```

- [ ] **Step 7: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`.

- [ ] **Step 8: Force-render and verify the embed, for both an ETF and a non-ETF company session**

Run:
```bash
cd app && python -c "
import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_beasiswa_setf_embed.db')
if os.path.exists(config.DB_PATH): os.remove(config.DB_PATH)
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
login = client.post('/auth/login', json={'username':'admin','password':'Admin@123'})
assert login.get_json()['ok']

# ETF company (company_id=2)
client.post('/select-company', data={'company_id': 2})
resp = client.get('/beasiswa/')
print('ETF STATUS', resp.status_code)
body = resp.data.decode('utf-8', errors='replace')
print('has tab-sahabat button:', 'data-tab=\"tab-sahabat\"' in body)
print('has tab-sahabat panel:', 'id=\"tab-sahabat\"' in body)
print('has real setf dashboard content (ETF):', 'id=\"setf-summary\"' in body)
print('has wrong-company notice (should be False for ETF):', 'Program khusus Eka Tjipta Foundation' in body)
print('old external link gone:', 'Sahabat ETF ↗' not in body)
print('loads sahabat_etf.js:', 'js/sahabat_etf.js' in body)

# SMT company (company_id=1)
client.post('/select-company', data={'company_id': 1})
resp2 = client.get('/beasiswa/')
print('SMT STATUS', resp2.status_code)
body2 = resp2.data.decode('utf-8', errors='replace')
print('has wrong-company notice (should be True for SMT):', 'Program khusus Eka Tjipta Foundation' in body2)
print('has real setf dashboard content (should be False for SMT):', 'id=\"setf-summary\"' in body2)

os.remove(config.DB_PATH)
"
```
Expected: `ETF STATUS 200`, all ETF-scenario checks `True` except the wrong-company one (`False`); `SMT STATUS 200`, wrong-company check `True` and setf-summary check `False`.

- [ ] **Step 9: Id-collision check**

Run:
```bash
cd app && python -c "
import os, sys, re
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_setf_id_collision.db')
if os.path.exists(config.DB_PATH): os.remove(config.DB_PATH)
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
login = client.post('/auth/login', json={'username':'admin','password':'Admin@123'})
client.post('/select-company', data={'company_id': 2})
resp = client.get('/beasiswa/')
body = resp.data.decode('utf-8', errors='replace')
ids = re.findall(r'id=\"([^\"]+)\"', body)
dupes = sorted(set(i for i in ids if ids.count(i) > 1))
print('Duplicate ids in rendered /beasiswa/ page:', dupes)
os.remove(config.DB_PATH)
"
```
Expected: the only entries in `dupes` (if any) are `chart-keluarga` and `setf-family-table` — the pre-existing bug documented in Global Constraints, already present before this task, carried over unchanged. Any OTHER id in that list is a real collision introduced by this task and must be fixed before proceeding (rename the colliding id in the Sahabat ETF partial only — do not touch ids belonging to other tabs).

- [ ] **Step 10: Commit**

```bash
git add app/templates/beasiswa/index.html
git commit -m "feat: embed Sahabat ETF as the 7th tab in Beasiswa"
```

---

## Task 4: Redirect the old standalone Sahabat ETF URL

**Files:**
- Modify: `app/modules/sahabat_etf/routes.py:1-66`

**Interfaces:**
- Consumes: `flask.redirect`, `flask.url_for`
- Produces: `GET /beasiswa/sahabat/` now returns a 302 redirect to `/beasiswa/?tab=sahabat` instead of rendering a page

- [ ] **Step 1: Confirm current route content**

Run: `cd app && sed -n '55,67p' modules/sahabat_etf/routes.py`
Expected:
```python
@bp.route("/")
@jwt_html_required
def index():
    cid = _cid()
    return render_template(
        "sahabat_etf/index.html",
        active_page="sahabat_etf",
        wrong_company=(session.get("company_code") != "ETF"),
        available_years=get_available_years(cid),
        available_pillars=get_available_pillars(cid),
        **_ctx(),
    )
```

- [ ] **Step 2: Add the `redirect`/`url_for` import**

Find (line 2):

```python
from flask import Blueprint, render_template, session, jsonify, request
```

Replace with:

```python
from flask import Blueprint, render_template, session, jsonify, request, redirect, url_for
```

- [ ] **Step 3: Replace the route body**

Find (the exact block from Step 1):

```python
@bp.route("/")
@jwt_html_required
def index():
    cid = _cid()
    return render_template(
        "sahabat_etf/index.html",
        active_page="sahabat_etf",
        wrong_company=(session.get("company_code") != "ETF"),
        available_years=get_available_years(cid),
        available_pillars=get_available_pillars(cid),
        **_ctx(),
    )
```

Replace with:

```python
@bp.route("/")
@jwt_html_required
def index():
    # The standalone page is now embedded as a tab in Beasiswa (see
    # templates/beasiswa/index.html's tab-sahabat panel) — redirect old
    # bookmarks/links there instead of rendering a separate page.
    return redirect(url_for("beasiswa.index", tab="sahabat"))
```

- [ ] **Step 4: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`.

- [ ] **Step 5: Force-render and verify the redirect**

Run:
```bash
cd app && python -c "
import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_setf_redirect.db')
if os.path.exists(config.DB_PATH): os.remove(config.DB_PATH)
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
login = client.post('/auth/login', json={'username':'admin','password':'Admin@123'})
assert login.get_json()['ok']
client.post('/select-company', data={'company_id': 2})
resp = client.get('/beasiswa/sahabat/', follow_redirects=False)
print('STATUS', resp.status_code)
print('LOCATION', resp.headers.get('Location'))
os.remove(config.DB_PATH)
"
```
Expected: `STATUS 302`, `LOCATION` ending in `/beasiswa/?tab=sahabat`.

- [ ] **Step 6: Confirm the API/export routes are untouched**

Run: `cd /c/Financehub && git diff app/modules/sahabat_etf/routes.py`

Expected: the diff shows changes ONLY inside the `index()` function (the import line from Step 2 and the function body from Step 3) — every `@bp.route("/api/...")` and `@bp.route("/export/...")` decorator, function signature, and body (lines ~69–185 of the original file: `api_summary`, `api_breakdown`, `api_monthly`, `api_family_summary`, `api_latest_payments`, `api_detail`, `export_summary`, `export_detail`, `export_report`, and the `etf_company_required` decorator definition) must show zero `+`/`-` lines. If any of those show up in the diff, stop — something unrelated got swept in; isolate and revert it before committing (see the shared-checkout caution in your dispatch: never `git add -A`/`git stash`/`git checkout` to fix this, hand-edit the file back instead).

- [ ] **Step 7: Commit**

```bash
git add app/modules/sahabat_etf/routes.py
git commit -m "feat: redirect standalone Sahabat ETF URL to its Beasiswa tab"
```

---

## Task 5: Add idempotency guard to `initSahabatEtf()`

**Files:**
- Modify: `app/static/js/sahabat_etf.js:652-672`

**Interfaces:**
- Consumes: nothing new
- Produces: `initSahabatEtf()` is now safe to call more than once (only the first call has effect) — required because Task 3's tab button calls it via `onclick` every time the tab is clicked, unlike the standalone page's one-time `DOMContentLoaded` call

- [ ] **Step 1: Confirm current function content**

Run: `cd app && sed -n '652,672p' static/js/sahabat_etf.js`
Expected:
```javascript
function initSahabatEtf() {
  document.querySelectorAll(".setf-year-cb").forEach(function (cb) {
    cb.addEventListener("change", setfApplyFilters);
  });
  document.querySelectorAll(".setf-pillar-cb").forEach(function (cb) {
    cb.addEventListener("change", setfApplyFilters);
  });
  const selectAllBtn = document.getElementById("setf-year-select-all");
  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", function () {
      document.querySelectorAll(".setf-year-cb").forEach(function (cb) { cb.checked = true; });
      setfApplyFilters();
    });
  }
  const reportYearSelect = document.getElementById("setf-report-year");
  if (reportYearSelect) {
    reportYearSelect.addEventListener("change", setfUpdateReportExportLink);
    setfUpdateReportExportLink();
  }
  setfApplyFilters();
}
```

- [ ] **Step 2: Add the guard**

Replace the block from Step 1 with:

```javascript
function initSahabatEtf() {
  // Hanya inisialisasi satu kali — dipanggil dari onclick tombol tab
  // "Sahabat ETF" di Beasiswa setiap kali tab diklik, tidak hanya sekali
  // seperti DOMContentLoaded pada halaman standalone-nya.
  if (window._sahabatInitialized) return;
  window._sahabatInitialized = true;

  document.querySelectorAll(".setf-year-cb").forEach(function (cb) {
    cb.addEventListener("change", setfApplyFilters);
  });
  document.querySelectorAll(".setf-pillar-cb").forEach(function (cb) {
    cb.addEventListener("change", setfApplyFilters);
  });
  const selectAllBtn = document.getElementById("setf-year-select-all");
  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", function () {
      document.querySelectorAll(".setf-year-cb").forEach(function (cb) { cb.checked = true; });
      setfApplyFilters();
    });
  }
  const reportYearSelect = document.getElementById("setf-report-year");
  if (reportYearSelect) {
    reportYearSelect.addEventListener("change", setfUpdateReportExportLink);
    setfUpdateReportExportLink();
  }
  setfApplyFilters();
}
```

- [ ] **Step 3: Structural verification**

Run:
```bash
cd app && python3 -c "
src = open('static/js/sahabat_etf.js', encoding='utf-8').read()
start = src.index('function initSahabatEtf()')
body = src[start:start+400]
assert '_sahabatInitialized' in body, 'guard missing'
assert body.count('function initSahabatEtf') == 1
print('STRUCTURAL_OK')
"
```
Expected: `STRUCTURAL_OK`.

- [ ] **Step 4: Commit**

```bash
git add app/static/js/sahabat_etf.js
git commit -m "fix: guard initSahabatEtf() against re-running on repeated tab clicks"
```

---

## Task 6: Deep-link support in the shared `initTabs()` helper

**Files:**
- Modify: `app/static/js/app.js:316-353`

**Interfaces:**
- Consumes: `window.location.search` (standard browser API)
- Produces: `initTabs(container)` now selects the tab matching a `?tab=<name>` query param (mapped to `[data-tab="tab-<name>"]`) if present and found, falling back to today's behavior (click the first tab) otherwise — used by Task 4's redirect target (`?tab=sahabat` → clicks `[data-tab="tab-sahabat"]`)

- [ ] **Step 1: Confirm current function content**

Run: `cd app && sed -n '316,353p' static/js/app.js`
Expected:
```javascript
function initTabs(container) {
  const tabs = container.querySelectorAll(".tab-btn");
  const panels = container.querySelectorAll(".tab-panel");
  const filterBtn = container.querySelector(".btn-filter-toggle");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const target = container.querySelector(`#${btn.dataset.tab}`);
      if (target) target.classList.add("active");
      // Filter panel always starts collapsed when switching sub-modules —
      // see docs/superpowers/specs/2026-07-12-financehub-page-toolbar-layout-design.md §2.3
      container.querySelectorAll(".filter-bar.collapsible.open").forEach(p => p.classList.remove("open"));
      if (filterBtn) {
        filterBtn.classList.remove("active");
        updateFilterBadge(filterBtn.id, 0);
        // Hide the Filter toggle entirely on tabs with no filter panel (e.g. a
        // single-record detail/report tab) instead of leaving an inert button.
        const hasFilterPanel = !!(target && target.querySelector(".filter-bar.collapsible"));
        filterBtn.style.display = hasFilterPanel ? "" : "none";
      }
      // Newly-active panel's own scroll-height wrapper (if any) was hidden a
      // moment ago and may have a stale computed height — modules that size
      // their table wrap dynamically (e.g. sizeWrap()-style code) already
      // listen for "resize", so re-dispatch it once the new panel is visible.
      window.dispatchEvent(new Event("resize"));
    });
  });
  if (filterBtn) {
    container.querySelectorAll(".filter-bar.collapsible").forEach(panel => {
      const recompute = () => refreshFilterBadge(panel, filterBtn.id);
      panel.addEventListener("input", recompute);
      panel.addEventListener("change", recompute);
    });
  }
  if (tabs.length > 0) tabs[0].click();
}
```

- [ ] **Step 2: Replace the final line**

Find (the exact end of the function from Step 1):

```javascript
  if (filterBtn) {
    container.querySelectorAll(".filter-bar.collapsible").forEach(panel => {
      const recompute = () => refreshFilterBadge(panel, filterBtn.id);
      panel.addEventListener("input", recompute);
      panel.addEventListener("change", recompute);
    });
  }
  if (tabs.length > 0) tabs[0].click();
}
```

Replace with:

```javascript
  if (filterBtn) {
    container.querySelectorAll(".filter-bar.collapsible").forEach(panel => {
      const recompute = () => refreshFilterBadge(panel, filterBtn.id);
      panel.addEventListener("input", recompute);
      panel.addEventListener("change", recompute);
    });
  }
  // Deep-link support: ?tab=<name> selects [data-tab="tab-<name>"] instead
  // of always defaulting to the first tab — used by redirects like
  // /beasiswa/sahabat -> /beasiswa/?tab=sahabat. Falls back to today's
  // default behavior when absent or no match is found.
  const requestedTab = new URLSearchParams(window.location.search).get("tab");
  const requested = requestedTab && container.querySelector(`[data-tab="tab-${requestedTab}"]`);
  if (requested) {
    requested.click();
  } else if (tabs.length > 0) {
    tabs[0].click();
  }
}
```

- [ ] **Step 3: Structural verification**

Run:
```bash
cd app && python3 -c "
src = open('static/js/app.js', encoding='utf-8').read()
start = src.index('function initTabs(container)')
end = src.index('\nfunction fmtRupiah')
body = src[start:end]
assert 'URLSearchParams(window.location.search).get(\"tab\")' in body
assert body.count('tabs[0].click()') == 1, 'must still have exactly one unconditional-fallback click call'
print('STRUCTURAL_OK')
"
```
Expected: `STRUCTURAL_OK`.

- [ ] **Step 4: Commit**

```bash
git add app/static/js/app.js
git commit -m "feat: support ?tab= deep-linking in the shared initTabs() helper"
```

---

## Task 7: Final verification — end-to-end + regression

**Files:**
- None modified (verification only)

**Interfaces:**
- Consumes: everything from Tasks 1-6

- [ ] **Step 1: Force-render the full redirect-to-tab flow end-to-end**

Run:
```bash
cd app && python -c "
import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_setf_e2e.db')
if os.path.exists(config.DB_PATH): os.remove(config.DB_PATH)
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
login = client.post('/auth/login', json={'username':'admin','password':'Admin@123'})
assert login.get_json()['ok']
client.post('/select-company', data={'company_id': 2})

# Old bookmark follows the redirect all the way to a working embedded tab
resp = client.get('/beasiswa/sahabat/', follow_redirects=True)
print('FOLLOWED STATUS', resp.status_code)
body = resp.data.decode('utf-8', errors='replace')
print('landed on beasiswa page with sahabat tab present:', 'data-tab=\"tab-sahabat\"' in body)
print('has real setf content:', 'id=\"setf-summary\"' in body)

os.remove(config.DB_PATH)
"
```
Expected: `FOLLOWED STATUS 200`, both checks `True`.

- [ ] **Step 2: Full Python regression suite**

Run: `cd app && python -m pytest tests/test_pam_pa_cascade.py tests/test_pam_remove_student.py tests/test_beasiswa_service.py tests/test_payment_memo_service.py -q`
Expected: same pass/fail counts as the prior Beasiswa Dashboard plans' final checks (no data-layer changes in this plan, only routing/rendering) — investigate anything new; pre-existing/unrelated failures already documented in this project's Known Issues are expected.

- [ ] **Step 3: Manual browser check (if a preview session with non-production data is available)**

From `/beasiswa/`, click through all 7 tabs and confirm: no page reload, tab bar stays visible throughout, Sahabat ETF's charts/tables populate correctly on first click. Then navigate directly to `/beasiswa/sahabat` and confirm it redirects and lands with the Sahabat ETF tab already selected and populated (not defaulting to Dashboard). Skip if only the shared live production DB is reachable.

- [ ] **Step 4: Confirm zero unintended blast radius**

Run: `cd /c/Financehub && git diff --stat <task-1-base-commit> HEAD -- app/modules/sahabat_etf/service.py app/templates/budget/dashboard.html app/static/css/budget.css`

(Substitute `<task-1-base-commit>` with the actual commit recorded before Task 1 started.)

Expected: empty output for all 3 files — this plan never touches the Sahabat ETF data layer or any file outside the 6 files modified across Tasks 1-6 (`sahabat_etf/index.html`, `sahabat_etf/_panel.html` [new], `beasiswa/routes.py`, `beasiswa/index.html`, `sahabat_etf/routes.py`, `sahabat_etf.js`, `app.js`).
