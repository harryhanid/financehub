# Sahabat ETF Dashboard/Laporan/Detail Transaksi Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the Sahabat ETF panel's single scrolling page into 3 tabs — Dashboard (existing content, unchanged), Laporan (new on-screen HTML rendering of the existing Excel report), Detail Transaksi (new on-screen list of every budget+payment transaction) — reusing `build_report_data()` and `get_all_transactions()` exactly as they exist today.

**Architecture:** New JSON endpoints expose the two existing data functions; a new, separately-classed sub-tab widget (not the site-wide `initTabs()`) switches between 3 panels; new JS render functions turn each endpoint's JSON into an HTML table, following this file's established fetch-JSON-render-HTML pattern.

**Tech Stack:** Flask + Jinja2 template with inline vanilla JS, plain CSS (no build step) — unchanged from every other Sahabat ETF/Beasiswa page in this codebase.

**Spec:** `docs/superpowers/specs/2026-08-03-sahabat-etf-tabs-laporan-detail-transaksi-design.md`

## Global Constraints

- Zero changes to `build_report_data()`, `build_report_workbook()`, `get_all_transactions()`, `report_xlsx.py`, or the existing `/export/report` and `/export/detail` download routes.
- Zero changes to the Dashboard tab's 3 existing accordions' internal content, chart IDs, or table IDs.
- The new sub-tab widget uses its own classes (`.setf-subtabs` / `.setf-subtab-btn` / `.setf-subtab-panel`) — never `.tabs` / `.tab-btn` / `.tab-panel` (those belong to the site-wide `initTabs()` in `app.js:445`, already active for Beasiswa's outer tab bar on the same page).
- The Detail Transaksi tab's Tahun/Pillar filter chips are a separate instance from the Dashboard tab's — different checkbox classes (`.setf-detail-year-cb` / `.setf-detail-pillar-cb`, not `.setf-year-cb` / `.setf-pillar-cb`), and `initFilterChips()` (the existing generic chip-wiring helper in `app.js:792`) is called once per tab, each scoped to that tab's own container element — never scoped to `document`, which would double-wire or cross-wire the two filter sets.
- Money values from the new endpoints are raw Rupiah (unchanged from `build_report_data()`/`get_all_transactions()`'s existing contract) — display formatting uses the existing `setfFmtJutaan()` helper, same as every other value already on this page.
- New route function names must not collide with the existing `api_detail(siswa_code)` (`/api/detail/<siswa_code>`, `routes.py:114`) — the new all-transactions endpoint is named `api_all_transactions()` at `/api/all_transactions`.

---

## Task 1: Backend — `GET /api/report` and `GET /api/all_transactions`

**Files:**
- Modify: `app/modules/sahabat_etf/routes.py`
- Test: `app/tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `build_report_data(company_id, report_year)`, `get_all_transactions(company_id, years, pillars)`, `_cid()`, `_parse_filters()`, `etf_company_required`, `jwt_html_required` — all already defined/imported in this file.
- Produces: `GET /beasiswa/sahabat/api/report?year=<int>` → `{"ok": true, "data": {...}}` (the exact dict `build_report_data()` returns); `GET /beasiswa/sahabat/api/all_transactions?years=&pillars=` → `{"ok": true, "rows": [...]}` — both consumed by Tasks 5 and 6's JS.

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_sahabat_etf_routes.py`:

```python
def test_api_report_returns_report_data(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/api/report?year=2026")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["data"]["report_year"] == 2026
    assert "sections" in data["data"]
    assert "pillar_breakdown" in data["data"]


def test_api_report_requires_year_param(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/api/report")
    assert resp.status_code == 400


def test_api_report_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/report?year=2026")
    assert resp.status_code == 403


def test_api_all_transactions_returns_rows(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/api/all_transactions")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert "rows" in data


def test_api_all_transactions_returns_403_for_non_etf_company(client):
    login(client)
    _select_smt(client)
    resp = client.get("/beasiswa/sahabat/api/all_transactions")
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_sahabat_etf_routes.py -k "api_report or api_all_transactions" -v`
Expected: FAIL with `404 NOT FOUND` for both new routes (they don't exist yet).

- [ ] **Step 3: Add the two routes in `app/modules/sahabat_etf/routes.py`**

Add after the existing `/api/detail/<siswa_code>` route (after its function body, before `/export/summary`):

```python
@bp.route("/api/report")
@jwt_html_required
@etf_company_required
def api_report():
    year_param = request.args.get("year", "")
    if not year_param.strip().lstrip("-").isdigit():
        return jsonify({"ok": False, "pesan": "Parameter year wajib berupa angka."}), 400
    return jsonify({"ok": True, "data": build_report_data(_cid(), int(year_param))})


@bp.route("/api/all_transactions")
@jwt_html_required
@etf_company_required
def api_all_transactions():
    years, pillars = _parse_filters()
    return jsonify({"ok": True, "rows": get_all_transactions(_cid(), years, pillars)})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_sahabat_etf_routes.py -k "api_report or api_all_transactions" -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full route test file to confirm no regressions**

Run: `cd app && python -m pytest tests/test_sahabat_etf_routes.py -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
cd /c/Financehub
git add app/modules/sahabat_etf/routes.py app/tests/test_sahabat_etf_routes.py
git commit -m "feat: add /api/report and /api/all_transactions endpoints for Sahabat ETF tabs"
```

---

## Task 2: CSS — sub-tab widget and Laporan table styling

**Files:**
- Modify: `app/static/css/budget.css`

**Interfaces:**
- Produces: `.setf-subtabs`, `.setf-subtab-btn`, `.setf-subtab-btn.active`, `.setf-subtab-panel`, `.setf-subtab-panel.active` (consumed by Task 3's markup and Task 4's JS); `.setf-laporan-table`, `.setf-laporan-section-title`, `.setf-laporan-subtotal-row`, `.setf-laporan-total-row`, `.setf-laporan-recap-row`, `.setf-laporan-pct-row` (consumed by Task 5's JS).

- [ ] **Step 1: Confirm current state before editing**

Run: `cd app && grep -c "setf-subtabs" static/css/budget.css`
Expected: `0` (class doesn't exist yet)

- [ ] **Step 2: Append the new rules to the end of `app/static/css/budget.css`**

```css

/* ── Sahabat ETF sub-tabs (Dashboard/Laporan/Detail Transaksi) ──────────────
   Separate classes from the site-wide .tabs/.tab-btn/.tab-panel (app.js's
   initTabs(), already active for Beasiswa's own outer tab bar on this same
   page) — visually identical, but must not share a selector or the two
   tab-switchers would double-handle clicks. See
   docs/superpowers/specs/2026-08-03-sahabat-etf-tabs-laporan-detail-transaksi-design.md */
.setf-subtabs {
  display: flex; flex-wrap: wrap;
  gap: .4rem;
  margin-bottom: 1.25rem;
}
.setf-subtab-btn {
  display: inline-flex; align-items: center;
  padding: .5rem 1rem;
  border: none; background: var(--bg-muted);
  border-radius: 999px;
  font-size: .8rem; font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  white-space: nowrap;
  font-family: inherit;
  transition: background .15s, color .15s, box-shadow .15s;
}
.setf-subtab-btn.active {
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: #fff;
  box-shadow: 0 4px 14px rgba(45,106,223,.3);
}
.setf-subtab-btn:hover:not(.active) { background: var(--accent-surface); color: var(--accent-text); }
.setf-subtab-panel { display: none; }
.setf-subtab-panel.active { display: block; }

/* ── Sahabat ETF Laporan tab — on-screen report table ────────────────────── */
.setf-laporan-table { width: 100%; border-collapse: collapse; margin-bottom: .75rem; font-size: .8rem; }
.setf-laporan-table th, .setf-laporan-table td { padding: .35rem .6rem; border-bottom: 1px solid var(--border); }
.setf-laporan-section-title { margin: 1rem 0 .5rem; font-size: .9rem; font-weight: 700; color: var(--text); }
.setf-laporan-subtotal-row { font-weight: 600; background: var(--bg-muted); }
.setf-laporan-total-row { font-weight: 700; background: var(--accent-surface); }
.setf-laporan-recap-row { font-style: italic; color: var(--text-muted); }
.setf-laporan-pct-row { font-size: .72rem; color: var(--text-muted); }
```

- [ ] **Step 3: Confirm braces are balanced**

Run: `cd app && python3 -c "s = open('static/css/budget.css', encoding='utf-8').read(); print(s.count('{') == s.count('}'))"`
Expected: `True`

- [ ] **Step 4: Confirm the new rules are present**

Run: `cd app && grep -c "setf-subtab-btn\|setf-laporan-table" static/css/budget.css`
Expected: `4` (2 occurrences of `.setf-subtab-btn`/`.setf-subtab-btn.active`/`.setf-subtab-btn:hover` count as separate lines — run the grep and confirm it's non-zero and matches the pasted block; exact count depends on how many lines contain these substrings, so treat "non-zero, no errors" as the pass condition rather than a brittle exact number)

- [ ] **Step 5: Commit**

```bash
cd /c/Financehub
git add app/static/css/budget.css
git commit -m "feat: add sub-tab widget and Laporan table CSS for Sahabat ETF"
```

---

## Task 3: Template — restructure `_panel.html` into 3 sub-tab panels

**Files:**
- Modify: `app/templates/sahabat_etf/_panel.html` (full-file replace — nearly every section moves or gets a new wrapper)
- Test: `app/tests/test_sahabat_etf_routes.py`

**Interfaces:**
- Consumes: `.setf-subtabs`/`.setf-subtab-btn`/`.setf-subtab-panel` CSS from Task 2; `url_for('sahabat_etf.export_summary')`, `url_for('sahabat_etf.export_detail')`, `url_for('sahabat_etf.export_report', year=...)` (existing routes, unchanged); `available_years`, `available_pillars` (existing template variables, unchanged).
- Produces: `setf-subtab-dashboard`, `setf-subtab-laporan`, `setf-subtab-detail` panel IDs and `setf-laporan-content`, `setf-detail-table` container IDs — consumed by Tasks 4-6's JS.

- [ ] **Step 1: Write the failing test**

Add to `app/tests/test_sahabat_etf_routes.py`:

```python
def test_index_contains_subtab_elements_for_etf_company(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/sahabat/")
    assert resp.status_code == 200
    for expected in (b'data-subtab="dashboard"', b'data-subtab="laporan"', b'data-subtab="detail"',
                      b'id="setf-subtab-dashboard"', b'id="setf-subtab-laporan"', b'id="setf-subtab-detail"',
                      b'id="setf-laporan-content"', b'id="setf-detail-table"',
                      b'setf-detail-year-cb', b'setf-detail-pillar-cb'):
        assert expected in resp.data, f"missing {expected!r} in response"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_sahabat_etf_routes.py -k subtab_elements -v`
Expected: FAIL (`b'data-subtab="dashboard"'` not in response — none of the new markup exists yet)

- [ ] **Step 3: Replace the entire content of `app/templates/sahabat_etf/_panel.html`**

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

  <div class="setf-subtabs">
    <button type="button" class="setf-subtab-btn active" data-subtab="dashboard">Dashboard</button>
    <button type="button" class="setf-subtab-btn" data-subtab="laporan">Laporan</button>
    <button type="button" class="setf-subtab-btn" data-subtab="detail">Detail Transaksi</button>
  </div>

  <div class="setf-subtab-panel active" id="setf-subtab-dashboard">

  <details class="setf-accordion" open>
    <summary>Ringkasan &amp; Alert</summary>
    <div class="setf-accordion-body">
      <div class="filter-bar beasiswa-dash-filterbar">
        <div class="beasiswa-dash-filter-chip">
          <span class="lbl">Tahun</span>
          <span class="val">Semua</span>
          <span class="caret">▾</span>
          <div class="beasiswa-dash-filter-panel">
            <div class="panel-head">
              <button type="button" data-act="all">Semua</button>
              <button type="button" data-act="none">Kosongkan</button>
            </div>
            <div class="panel-opts" id="setf-filter-tahun">
              {% for y in available_years %}
              <label><input type="checkbox" class="setf-year-cb" value="{{ y }}" checked> {{ y }}</label>
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
            <div class="panel-opts" id="setf-filter-pillar">
              {% for p in available_pillars %}
              <label><input type="checkbox" class="setf-pillar-cb" value="{{ p }}" checked> {{ p }}</label>
              {% endfor %}
            </div>
          </div>
        </div>
      </div>

      <div class="budget-toolbar">
        <a class="budget-btn" id="setf-export-summary" href="{{ url_for('sahabat_etf.export_summary') }}">Export Ringkasan (CSV)</a>
        <button type="button" class="budget-btn" id="setf-export-pdf" onclick="setfExportPdf()">Export PDF (Print)</button>
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

        <div class="budget-chart-card"><h3>Realisasi per Sahabat</h3><canvas id="chart-keluarga"></canvas></div>
        <div class="budget-chart-card setf-compact-card">
          <h3>Realisasi per Sahabat (Tabel)</h3>
          <div class="setf-compact-scroll">
            <table id="setf-family-table">
              <thead><tr><th>Sahabat</th><th>Nama</th><th>Kategori Realisasi</th><th class="num-right">Realisasi</th></tr></thead>
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

  </div>

  <div class="setf-subtab-panel" id="setf-subtab-laporan">
    <div class="filter-bar">
      <div class="filter-field">
        <label>Tahun Report</label>
        <select id="setf-report-year">
          {% for y in available_years|reverse %}
          <option value="{{ y }}">{{ y }}</option>
          {% endfor %}
        </select>
      </div>
    </div>
    <div class="budget-toolbar">
      <a class="budget-btn" id="setf-export-report" href="{{ url_for('sahabat_etf.export_report', year=available_years|first or 2026) }}">Export Laporan (Excel)</a>
    </div>
    <div id="setf-laporan-content">
      <p style="color:var(--text-muted);text-align:center;padding:2rem">Memuat laporan...</p>
    </div>
  </div>

  <div class="setf-subtab-panel" id="setf-subtab-detail">
    <div class="filter-bar beasiswa-dash-filterbar">
      <div class="beasiswa-dash-filter-chip">
        <span class="lbl">Tahun</span>
        <span class="val">Semua</span>
        <span class="caret">▾</span>
        <div class="beasiswa-dash-filter-panel">
          <div class="panel-head">
            <button type="button" data-act="all">Semua</button>
            <button type="button" data-act="none">Kosongkan</button>
          </div>
          <div class="panel-opts" id="setf-detail-filter-tahun">
            {% for y in available_years %}
            <label><input type="checkbox" class="setf-detail-year-cb" value="{{ y }}" checked> {{ y }}</label>
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
          <div class="panel-opts" id="setf-detail-filter-pillar">
            {% for p in available_pillars %}
            <label><input type="checkbox" class="setf-detail-pillar-cb" value="{{ p }}" checked> {{ p }}</label>
            {% endfor %}
          </div>
        </div>
      </div>
    </div>

    <div class="budget-toolbar">
      <a class="budget-btn" id="setf-export-detail" href="{{ url_for('sahabat_etf.export_detail') }}">Export Detail Transaksi (CSV)</a>
    </div>

    <div class="table-wrap">
      <table id="setf-detail-table">
        <thead>
          <tr><th>Sumber</th><th>Kode Siswa</th><th>Nama</th><th>Tanggal</th><th>Kategori 1</th><th>Kategori 2</th><th class="num-right">Amount</th><th>Status</th></tr>
        </thead>
        <tbody><tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
      </table>
    </div>
  </div>

  {% endif %}
</div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_sahabat_etf_routes.py -k subtab_elements -v`
Expected: PASS

- [ ] **Step 5: Confirm the 9 existing chart/table IDs from the Dashboard tab are still present exactly once each (nothing dropped or duplicated during the restructure)**

Run:
```bash
cd app && python3 -c "
src = open('templates/sahabat_etf/_panel.html', encoding='utf-8').read()
for cid in ['chart-bulanan', 'chart-tahunan', 'setf-monthly-table', 'setf-pillar-table',
            'chart-keluarga', 'setf-family-table', 'chart-kategori', 'setf-kategori-table',
            'setf-latest-payments-table', 'setf-table']:
    count = src.count('id=\"' + cid + '\"')
    assert count == 1, cid + ' appears ' + str(count) + ' times, expected 1'
print('DASHBOARD_IDS_OK')
"
```
Expected: `DASHBOARD_IDS_OK`

- [ ] **Step 6: Run the full route test file to confirm no regressions**

Run: `cd app && python -m pytest tests/test_sahabat_etf_routes.py -v`
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
cd /c/Financehub
git add app/templates/sahabat_etf/_panel.html app/tests/test_sahabat_etf_routes.py
git commit -m "feat: restructure Sahabat ETF panel into Dashboard/Laporan/Detail Transaksi tabs"
```

---

## Task 4: JS — sub-tab switching and scoped filter-chip wiring

**Files:**
- Modify: `app/static/js/sahabat_etf.js`

**Interfaces:**
- Consumes: `.setf-subtab-btn`/`.setf-subtab-panel` markup from Task 3; `initFilterChips(root, onChange)` (existing generic helper, `app.js:792`); `setfApplyFilters()`, `setfUpdateReportExportLink()` (existing functions in this file).
- Produces: `initSetfSubtabs()` — called once from `initSahabatEtf()`; `window._setfLaporanLoaded` / `window._setfDetailLoaded` flags (lazy-load guards consumed by Tasks 5 and 6, which define `setfLoadLaporan()` and `setfLoadDetailTransaksi()` — this task calls them but does not define them, so this task's own manual verification in Step 6 will show a "not defined" console state until Tasks 5-6 land; that's expected and does not block committing this task, since `setfLoadLaporan`/`setfLoadDetailTransaksi` are called only on tab click, never during page load).

- [ ] **Step 1: Confirm current state before editing**

Run: `cd app && grep -n "^function initSahabatEtf" -A 15 static/js/sahabat_etf.js`
Expected output (the current version, before this task's edit):
```javascript
function initSahabatEtf() {
  // Hanya inisialisasi satu kali — dipanggil dari onclick tombol tab
  // "Sahabat ETF" di Beasiswa setiap kali tab diklik, tidak hanya sekali
  // seperti DOMContentLoaded pada halaman standalone-nya.
  if (window._sahabatInitialized) return;
  window._sahabatInitialized = true;

  initFilterChips(document, setfApplyFilters);
  const reportYearSelect = document.getElementById("setf-report-year");
  if (reportYearSelect) {
    reportYearSelect.addEventListener("change", setfUpdateReportExportLink);
    setfUpdateReportExportLink();
  }
  setfApplyFilters();
}
```

- [ ] **Step 2: Add `initSetfSubtabs()` above `initSahabatEtf()`**

Insert directly before the `function initSahabatEtf() {` line:

```javascript
function initSetfSubtabs() {
  const buttons = document.querySelectorAll(".setf-subtab-btn");
  const panels = document.querySelectorAll(".setf-subtab-panel");
  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      buttons.forEach(function (b) { b.classList.remove("active"); });
      panels.forEach(function (p) { p.classList.remove("active"); });
      btn.classList.add("active");
      const panel = document.getElementById("setf-subtab-" + btn.dataset.subtab);
      if (panel) panel.classList.add("active");
      if (btn.dataset.subtab === "laporan" && !window._setfLaporanLoaded) {
        window._setfLaporanLoaded = true;
        setfLoadLaporan();
      }
      if (btn.dataset.subtab === "detail" && !window._setfDetailLoaded) {
        window._setfDetailLoaded = true;
        setfLoadDetailTransaksi();
      }
    });
  });
}

```

- [ ] **Step 3: Update `initSahabatEtf()` to call it and scope the existing filter-chip wiring**

Replace:

```javascript
function initSahabatEtf() {
  // Hanya inisialisasi satu kali — dipanggil dari onclick tombol tab
  // "Sahabat ETF" di Beasiswa setiap kali tab diklik, tidak hanya sekali
  // seperti DOMContentLoaded pada halaman standalone-nya.
  if (window._sahabatInitialized) return;
  window._sahabatInitialized = true;

  initFilterChips(document, setfApplyFilters);
  const reportYearSelect = document.getElementById("setf-report-year");
  if (reportYearSelect) {
    reportYearSelect.addEventListener("change", setfUpdateReportExportLink);
    setfUpdateReportExportLink();
  }
  setfApplyFilters();
}
```

with:

```javascript
function initSahabatEtf() {
  // Hanya inisialisasi satu kali — dipanggil dari onclick tombol tab
  // "Sahabat ETF" di Beasiswa setiap kali tab diklik, tidak hanya sekali
  // seperti DOMContentLoaded pada halaman standalone-nya.
  if (window._sahabatInitialized) return;
  window._sahabatInitialized = true;

  initSetfSubtabs();
  // Scoped to each sub-tab's own container — Dashboard and Detail Transaksi
  // each have their own .beasiswa-dash-filter-chip instances (different
  // checkbox classes), so a document-wide call would wire both sets to the
  // same callback.
  initFilterChips(document.getElementById("setf-subtab-dashboard"), setfApplyFilters);
  initFilterChips(document.getElementById("setf-subtab-detail"), setfLoadDetailTransaksi);
  const reportYearSelect = document.getElementById("setf-report-year");
  if (reportYearSelect) {
    reportYearSelect.addEventListener("change", setfUpdateReportExportLink);
    reportYearSelect.addEventListener("change", function () {
      if (window._setfLaporanLoaded) setfLoadLaporan();
    });
    setfUpdateReportExportLink();
  }
  setfApplyFilters();
}
```

- [ ] **Step 4: Remove the "Export Detail Transaksi" line from `setfUpdateExportLinks()` (it now has its own tab-scoped update function, added in Task 6)**

Find (currently at `sahabat_etf.js:543-550`):

```javascript
function setfUpdateExportLinks(qs) {
  const summaryLink = document.getElementById("setf-export-summary");
  const detailLink = document.getElementById("setf-export-detail");
  const baseSummary = summaryLink.href.split("?")[0];
  const baseDetail = detailLink.href.split("?")[0];
  summaryLink.href = qs ? baseSummary + "?" + qs : baseSummary;
  detailLink.href = qs ? baseDetail + "?" + qs : baseDetail;
}
```

Replace with:

```javascript
function setfUpdateExportLinks(qs) {
  const summaryLink = document.getElementById("setf-export-summary");
  const baseSummary = summaryLink.href.split("?")[0];
  summaryLink.href = qs ? baseSummary + "?" + qs : baseSummary;
}
```

- [ ] **Step 5: Structural check**

Run:
```bash
cd app && python3 -c "
src = open('static/js/sahabat_etf.js', encoding='utf-8').read()
assert 'function initSetfSubtabs' in src
assert 'initFilterChips(document.getElementById(\"setf-subtab-dashboard\")' in src
assert 'initFilterChips(document.getElementById(\"setf-subtab-detail\")' in src
assert 'initFilterChips(document, setfApplyFilters)' not in src
assert src.count('function initSahabatEtf') == 1
print('JS_STRUCTURAL_OK')
"
```
Expected: `JS_STRUCTURAL_OK`

- [ ] **Step 6: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`

- [ ] **Step 7: Commit**

```bash
cd /c/Financehub
git add app/static/js/sahabat_etf.js
git commit -m "feat: add Sahabat ETF sub-tab switching, scope filter-chip wiring per tab"
```

---

## Task 5: JS — Laporan tab rendering

**Files:**
- Modify: `app/static/js/sahabat_etf.js`

**Interfaces:**
- Consumes: `GET /beasiswa/sahabat/api/report?year=<int>` (Task 1); `#setf-report-year`, `#setf-laporan-content` (Task 3 markup); `setfFmtJutaan()`, `showToast()` (existing helpers already used elsewhere in this file).
- Produces: `setfLoadLaporan()` — called by `initSetfSubtabs()` (Task 4) on first activation of the Laporan tab, and by the report-year `change` listener (Task 4) on subsequent year changes.

- [ ] **Step 1: Add the Laporan rendering functions to `app/static/js/sahabat_etf.js`**

Add at the end of the file:

```javascript

// ─── Laporan tab: on-screen rendering of the Excel report's data ────────────
function setfLaporanHeaderRow(reportYear) {
  return '<tr class="setf-laporan-header">' +
    '<th rowspan="2">Nama</th><th rowspan="2">Pillar</th>' +
    '<th colspan="4">Tahun ' + reportYear + '</th>' +
    '<th colspan="4">S/D Tahun ' + reportYear + '</th></tr>' +
    '<tr class="setf-laporan-header">' +
    '<th>Plafon</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th>' +
    '<th>Plafon</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th></tr>';
}

function setfLaporanMetricsCells(m) {
  return '<td class="num-right">' + setfFmtJutaan(m.cur.plafon) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cur.klaim) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cur.dibayar) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cur.saldo) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.plafon) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.klaim) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.dibayar) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.saldo) + '</td>';
}

function setfLaporanNamaRow(row, cls) {
  return '<tr class="' + cls + '"><td>' + row.nama + '</td><td>' + row.pillar + '</td>' +
    setfLaporanMetricsCells(row) + '</tr>';
}

function setfLaporanLabelRow(label, metrics, cls) {
  return '<tr class="' + cls + '"><td colspan="2">' + label + '</td>' +
    setfLaporanMetricsCells(metrics) + '</tr>';
}

function setfRenderLaporanSection(section, reportYear) {
  let html = '<h4 class="setf-laporan-section-title">' + section.label + '</h4>';
  html += '<table class="setf-laporan-table"><thead>' + setfLaporanHeaderRow(reportYear) + '</thead><tbody>';
  section.groups.forEach(function (group) {
    html += setfLaporanLabelRow(group.label, group.subtotal, 'setf-laporan-subtotal-row');
    group.siswa_rows.forEach(function (row) {
      html += setfLaporanNamaRow(row, 'setf-laporan-siswa-row');
    });
  });
  html += setfLaporanLabelRow('TOTAL ' + section.label, section.total, 'setf-laporan-total-row');
  html += '</tbody></table>';
  if (section.recap.length) {
    html += '<table class="setf-laporan-table setf-laporan-recap">' +
      '<caption>Rekap ' + section.label + '</caption><thead>' + setfLaporanHeaderRow(reportYear) + '</thead><tbody>';
    section.recap.forEach(function (row) {
      html += setfLaporanNamaRow(row, 'setf-laporan-recap-row');
    });
    html += '</tbody></table>';
  }
  return html;
}

function setfRenderLaporanPillarBreakdown(pillarBreakdown, grandTotal, reportYear) {
  let html = '<h4 class="setf-laporan-section-title">Breakdown Pillar</h4>';
  html += '<table class="setf-laporan-table"><thead>' + setfLaporanHeaderRow(reportYear) + '</thead><tbody>';
  html += setfLaporanLabelRow('GRAND TOTAL', grandTotal, 'setf-laporan-total-row');
  pillarBreakdown.forEach(function (p) {
    html += '<tr class="setf-laporan-subtotal-row"><td colspan="2">' + p.pillar_label + '</td>' +
      setfLaporanMetricsCells(p) + '</tr>';
    html += '<tr class="setf-laporan-pct-row"><td colspan="2">% to total</td>' +
      '<td class="num-right">' + (p.pct_cur.plafon * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cur.klaim * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cur.dibayar * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cur.saldo * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.plafon * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.klaim * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.dibayar * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.saldo * 100).toFixed(1) + '%</td></tr>';
  });
  html += '</tbody></table>';
  return html;
}

function setfRenderLaporan(data) {
  let html = '<h3>REPORT — Tahun ' + data.report_year + '</h3>';
  data.sections.forEach(function (section) {
    html += setfRenderLaporanSection(section, data.report_year);
  });
  html += '<h4 class="setf-laporan-section-title">Total Pendidikan &amp; Kesehatan</h4>';
  html += '<table class="setf-laporan-table"><thead>' + setfLaporanHeaderRow(data.report_year) + '</thead><tbody>';
  html += setfLaporanLabelRow('TOTAL PENDIDIKAN &amp; KESEHATAN', data.combined_total, 'setf-laporan-total-row');
  data.combined_recap.forEach(function (row) {
    html += setfLaporanNamaRow(row, 'setf-laporan-recap-row');
  });
  html += setfLaporanLabelRow('GRAND TOTAL', data.grand_total, 'setf-laporan-total-row');
  html += '</tbody></table>';
  html += setfRenderLaporanPillarBreakdown(data.pillar_breakdown, data.grand_total, data.report_year);
  document.getElementById('setf-laporan-content').innerHTML = html;
}

function setfLoadLaporan() {
  const sel = document.getElementById('setf-report-year');
  if (!sel) return;
  document.getElementById('setf-laporan-content').innerHTML =
    '<p style="color:var(--text-muted);text-align:center;padding:2rem">Memuat laporan...</p>';
  fetch('/beasiswa/sahabat/api/report?year=' + encodeURIComponent(sel.value))
    .then(function (r) { return r.json(); })
    .then(function (resp) {
      if (!resp.ok) { showToast(resp.pesan || 'Gagal memuat laporan.', 'error'); return; }
      setfRenderLaporan(resp.data);
    })
    .catch(function () { showToast('Gagal memuat laporan.', 'error'); });
}
```

- [ ] **Step 2: Structural check**

Run:
```bash
cd app && python3 -c "
src = open('static/js/sahabat_etf.js', encoding='utf-8').read()
for fn in ['setfLoadLaporan', 'setfRenderLaporan', 'setfRenderLaporanSection',
           'setfRenderLaporanPillarBreakdown', 'setfLaporanHeaderRow',
           'setfLaporanMetricsCells', 'setfLaporanNamaRow', 'setfLaporanLabelRow']:
    assert ('function ' + fn) in src, fn + ' not defined'
print('LAPORAN_JS_OK')
"
```
Expected: `LAPORAN_JS_OK`

- [ ] **Step 3: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`

- [ ] **Step 4: Commit**

```bash
cd /c/Financehub
git add app/static/js/sahabat_etf.js
git commit -m "feat: render Sahabat ETF Laporan tab from /api/report JSON"
```

---

## Task 6: JS — Detail Transaksi tab rendering

**Files:**
- Modify: `app/static/js/sahabat_etf.js`

**Interfaces:**
- Consumes: `GET /beasiswa/sahabat/api/all_transactions?years=&pillars=` (Task 1); `.setf-detail-year-cb`/`.setf-detail-pillar-cb`/`#setf-export-detail`/`#setf-detail-table` (Task 3 markup); `setfBuildQueryString()`, `setfFmtJutaan()`, `showToast()`, `skeletonRows()` (existing helpers already used elsewhere in this file).
- Produces: `setfLoadDetailTransaksi()` — called by `initSetfSubtabs()` (Task 4) on first activation of the Detail Transaksi tab, and passed as the `onChange` callback to `initFilterChips()` for that tab's filter chips (Task 4).

- [ ] **Step 1: Add the Detail Transaksi rendering functions to `app/static/js/sahabat_etf.js`**

Add at the end of the file:

```javascript

// ─── Detail Transaksi tab: full transaction list ────────────────────────────
function setfGetDetailFilters() {
  const years = Array.from(document.querySelectorAll(".setf-detail-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".setf-detail-pillar-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars };
}

function setfUpdateDetailExportLink(qs) {
  const link = document.getElementById("setf-export-detail");
  if (!link) return;
  const base = link.href.split("?")[0];
  link.href = qs ? base + "?" + qs : base;
}

function setfRenderDetailTable(rows) {
  const tbody = document.querySelector("#setf-detail-table tbody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Belum ada transaksi.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.sumber + "</td>" +
      "<td>" + r.siswa_code + "</td>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + r.tanggal + "</td>" +
      "<td>" + r.cat1 + "</td>" +
      "<td>" + (r.cat2 || "") + "</td>" +
      '<td class="num-right">' + setfFmtJutaan(r.amount) + "</td>" +
      "<td>" + (r.status || "") + "</td>" +
      "</tr>";
  }).join("");
}

function setfLoadDetailTransaksi() {
  const filters = setfGetDetailFilters();
  const qs = setfBuildQueryString(filters);
  setfUpdateDetailExportLink(qs);
  document.querySelector("#setf-detail-table tbody").innerHTML = skeletonRows(6, 8);
  fetch("/beasiswa/sahabat/api/all_transactions" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (resp) {
      if (!resp.ok) { showToast(resp.pesan || "Gagal memuat detail transaksi.", "error"); return; }
      setfRenderDetailTable(resp.rows);
    })
    .catch(function () { showToast("Gagal memuat detail transaksi.", "error"); });
}
```

- [ ] **Step 2: Structural check**

Run:
```bash
cd app && python3 -c "
src = open('static/js/sahabat_etf.js', encoding='utf-8').read()
for fn in ['setfLoadDetailTransaksi', 'setfRenderDetailTable', 'setfGetDetailFilters', 'setfUpdateDetailExportLink']:
    assert ('function ' + fn) in src, fn + ' not defined'
print('DETAIL_JS_OK')
"
```
Expected: `DETAIL_JS_OK`

- [ ] **Step 3: App-boot sanity check**

Run:
```bash
cd app && python -c "
from app import create_app
app = create_app()
print('APP_BOOT_OK')
"
```
Expected: `APP_BOOT_OK`

- [ ] **Step 4: Commit**

```bash
cd /c/Financehub
git add app/static/js/sahabat_etf.js
git commit -m "feat: render Sahabat ETF Detail Transaksi tab from /api/all_transactions JSON"
```

---

## Task 7: Final verification

**Files:**
- None modified (verification only)

**Interfaces:**
- Consumes: everything from Tasks 1-6

- [ ] **Step 1: Full Sahabat ETF + Beasiswa test suites**

Run: `cd app && python -m pytest tests/test_sahabat_etf_service.py tests/test_sahabat_etf_report_xlsx.py tests/test_sahabat_etf_routes.py tests/test_beasiswa_routes.py -v`
Expected: all tests pass (no changes to `service.py`/`report_xlsx.py` in this plan, so those two files' tests are an unaffected-regression check; `test_beasiswa_routes.py` covers the outer Beasiswa page that embeds this panel via `{% include %}`, confirming the restructure didn't break that page's own render).

- [ ] **Step 2: Manual browser check (if a preview session with non-production data is available)**

Open the Sahabat ETF panel (either standalone at `/beasiswa/sahabat/` or via Beasiswa's "Sahabat ETF" tab). Confirm: 3 sub-tab buttons render, Dashboard is active by default with all existing content intact; clicking "Laporan" loads and renders the report table (sections, subtotals, recap, grand total, pillar breakdown) for the default year, and changing the year re-loads it; clicking "Detail Transaksi" loads the full transaction list, and toggling its Tahun/Pillar filters re-loads it without affecting the Dashboard tab's own filters; "Export Laporan (Excel)" and "Export Detail Transaksi (CSV)" still download correctly from their new tabs. Skip if no preview/browser session with non-production data is available — do not block on it.

- [ ] **Step 3: Confirm zero blast radius outside Sahabat ETF**

Run: `cd /c/Financehub && git diff --stat HEAD~6 -- app/templates/beasiswa/index.html app/static/js/dashboard_beasiswa.js app/static/css/beasiswa_dashboard.css`

(Adjust `HEAD~6` if the actual number of commits from this plan's Tasks 1-6 differs.)

Expected: empty output for all 3 files, evaluated against **committed** state only.
