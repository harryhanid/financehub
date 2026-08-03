# Beasiswa Dashboard Card Reorder & Tidy-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split each Grafik panel's mixed chart+table card grid into type-grouped rows (chart cards together, table cards together) and move the "Rincian Budget vs Realisasi per Program" card from Detail Transaksi into Breakdown Realisasi, where it semantically belongs.

**Architecture:** Pure markup reorder inside `beasiswa/index.html`'s Grafik section — each of the 3 `.beasiswa-dash-section-panel` blocks gets its single `.beasiswa-dash-grafik-grid` split into one or two grids (chart-type cards, then table-type cards), reusing the existing CSS classes unchanged. No CSS or JS changes.

**Tech Stack:** Flask + Jinja2 template with inline vanilla JS, plain CSS (no build step) — unchanged from the two prior Beasiswa Dashboard redesigns this follows.

**Spec:** `docs/superpowers/specs/2026-08-03-beasiswa-dashboard-card-reorder-design.md`

## Global Constraints

- Zero backend/Python changes.
- Zero CSS changes — `app/static/css/beasiswa_dashboard.css` is not touched; all classes used already exist (`.beasiswa-dash-section-panel`, `.beasiswa-dash-section-title`, `.beasiswa-dash-grafik-grid`, `.beasiswa-dash-chart-card`, `.compact`).
- Zero JS changes — `app/static/js/dashboard_beasiswa.js` is not touched; no chart/table `id` moves, so every `dashRender*` function keeps targeting the same elements.
- The 9 existing chart/table card `id`s (`dash-chart-bulanan`, `dash-chart-tahunan`, `dash-monthly-table`, `dash-chart-kategori`, `dash-kategori-table`, `dash-jenjang-table`, `dash-pillar-year-table`, `dash-latest-payments-table`, `dash-program-table`) must each still appear exactly once after the change.
- No frontend test framework exists in this codebase — verification is app-boot + force-render (with a real test-DB login, not a fake session) + structural checks, matching the pattern established in the two prior Beasiswa Dashboard redesign plans.

---

## Task 1: Restructure Grafik section markup in `beasiswa/index.html`

**Files:**
- Modify: `app/templates/beasiswa/index.html:113-204`

**Interfaces:**
- Consumes: existing CSS classes only (`.beasiswa-dash-section-panel`, `.beasiswa-dash-section-title`, `.beasiswa-dash-grafik-grid`, `.beasiswa-dash-chart-card`, `.compact`, `.setf-compact-scroll`) — no new classes.
- Produces: no change to any chart/table `id` or JS render target — this is the only task in this plan.

- [ ] **Step 1: Confirm current state before editing**

Run: `cd app && grep -c "beasiswa-dash-grafik-grid" templates/beasiswa/index.html`
Expected: `3` (one grid per panel — baseline before this task's split)

Run: `cd app && grep -c "beasiswa-dash-chart-card" templates/beasiswa/index.html`
Expected: `9` (baseline card count — must stay `9` after this task)

- [ ] **Step 2: Replace the Grafik section block**

In `app/templates/beasiswa/index.html`, find the block from `<details class="setf-accordion" id="dash-grafik-accordion" open>` through its closing `</details>` (lines 113-203):

```html
      <details class="setf-accordion" id="dash-grafik-accordion" open>
        <summary>Grafik</summary>
        <div class="setf-accordion-body">
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
        </div>
      </details>
```

Replace with:

```html
      <details class="setf-accordion" id="dash-grafik-accordion" open>
        <summary>Grafik</summary>
        <div class="setf-accordion-body">
          <div class="beasiswa-dash-grafik-wrap">
            <div class="beasiswa-dash-section-panel">
              <div class="beasiswa-dash-section-title">Trend</div>
              <div class="beasiswa-dash-grafik-grid">
                <div class="beasiswa-dash-chart-card"><h3>Trend per Bulan</h3><canvas id="dash-chart-bulanan"></canvas></div>
                <div class="beasiswa-dash-chart-card"><h3>Trend per Tahun</h3><canvas id="dash-chart-tahunan"></canvas></div>
              </div>
              <div class="beasiswa-dash-grafik-grid">
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
              </div>
              <div class="beasiswa-dash-grafik-grid">
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
              </div>
            </div>
          </div>
        </div>
      </details>
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

- [ ] **Step 4: Force-render and verify the new structure**

Run:
```bash
cd app && python -c "
import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_dash_reorder_render.db')
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

print('chart-card count (must stay 9):', body.count('beasiswa-dash-chart-card'))
print('grafik-grid count (was 3, now 5):', body.count('beasiswa-dash-grafik-grid'))
print('section-panel count (must stay 3):', body.count('class=\"beasiswa-dash-section-panel\"'))

for cid in ['dash-chart-bulanan', 'dash-chart-tahunan', 'dash-monthly-table',
            'dash-chart-kategori', 'dash-kategori-table', 'dash-jenjang-table',
            'dash-pillar-year-table', 'dash-latest-payments-table', 'dash-program-table']:
    count = body.count('id=\"' + cid + '\"')
    print(cid, 'count:', count)
    assert count == 1, cid + ' must appear exactly once'

breakdown_idx = body.index('Breakdown Realisasi')
program_idx = body.index('dash-program-table')
detail_idx = body.index('Detail Transaksi')
print('Program card is between Breakdown Realisasi and Detail Transaksi titles:', breakdown_idx < program_idx < detail_idx)

detail_panel = body[detail_idx:]
print('Detail Transaksi panel has exactly 1 chart-card:', detail_panel[:detail_panel.index('</details>')].count('beasiswa-dash-chart-card') == 1)

os.remove(config.DB_PATH)
"
```
Expected: `STATUS 200`; `chart-card count (must stay 9): 9`; `grafik-grid count (was 3, now 5): 5`; `section-panel count (must stay 3): 3`; all 9 `id` counts equal `1`; `Program card is between Breakdown Realisasi and Detail Transaksi titles: True`; `Detail Transaksi panel has exactly 1 chart-card: True`.

- [ ] **Step 5: Confirm zero blast radius on CSS and JS**

Run: `cd /c/Financehub && git diff --stat -- app/static/css/beasiswa_dashboard.css app/static/js/dashboard_beasiswa.js`
Expected: empty output (proves neither file changed — this task is markup-only, per Global Constraints).

- [ ] **Step 6: Commit**

```bash
cd /c/Financehub
git add app/templates/beasiswa/index.html
git commit -m "feat: reorder and regroup Beasiswa Dashboard Grafik cards by type"
```
