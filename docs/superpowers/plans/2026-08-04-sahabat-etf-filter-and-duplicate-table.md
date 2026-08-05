# Sahabat ETF Filter Unification & Duplicate Table Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Sahabat ETF's Tahun/Pillar filters look and behave like Dashboard's dropdown-chip filters, and fix the "Realisasi per Sahabat" table in Detail Tabel that can never populate because it shares a duplicate `id` with a working copy elsewhere on the page.

**Architecture:** Extract Dashboard's already-generic chip-wiring code into a shared `initFilterChips(root, onChange)` helper in `app.js`, used by both Dashboard and (after this plan) Sahabat ETF. Convert Sahabat ETF's inline-checkbox filter markup to the same chip HTML structure Dashboard uses. Delete the duplicate table/chart block.

**Tech Stack:** Flask/Jinja2, vanilla JS, pytest.

## Global Constraints

- The "Tahun Report (Export Laporan)" `<select>` in Sahabat ETF is untouched — it's an export parameter, not a data filter.
- `setf-table` ("Rincian Budget vs Realisasi per Anggota") is untouched — already correctly wired, unique id.
- Dashboard's filter *behavior* must be identical before and after Task 1 — only its implementation location changes.
- Only these files change: `app/static/js/app.js`, `app/static/js/dashboard_beasiswa.js`, `app/static/js/sahabat_etf.js`, `app/templates/sahabat_etf/_panel.html`, `app/tests/test_beasiswa_routes.py`.

---

### Task 1: Extract the chip-filter wiring into a shared helper

**Files:**
- Modify: `app/static/js/app.js` (append near the end, before the final `DOMContentLoaded` listener)
- Modify: `app/static/js/dashboard_beasiswa.js:472-533`
- Test: `app/tests/test_beasiswa_routes.py`

**Interfaces:**
- Produces: `initFilterChips(root: Element|Document, onChange: () => void)`, `updateFilterChipSummary(chip: Element)` — both consumed by Task 2.

This task is a pure refactor — Dashboard's filter behavior must be
identical before and after. There's no new DOM-testable behavior to add a
route test for; the regression check is that Dashboard's existing markup
(chip classes) is still present and unchanged, which the existing test
suite already exercises indirectly by rendering the page successfully.

- [ ] **Step 1: Write a regression test for the page still rendering cleanly**

Check `app/tests/test_beasiswa_routes.py` for its `login`/`_select_etf`
helpers (already defined there, per the existing tests in this file) and
add:

```python
def test_dashboard_tab_still_has_filter_chips_after_refactor(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert resp.status_code == 200
    assert resp.data.count(b"beasiswa-dash-filter-chip") >= 4  # Tahun/Pillar/Program/Jenjang
```

- [ ] **Step 2: Run the test to verify it passes (baseline, before refactor)**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v -k filter_chips_after_refactor`
Expected: PASS — this test should already pass before any code changes; it's here to catch a regression once Task 1's refactor lands, not to drive new behavior.

- [ ] **Step 3: Add the shared helper to `app.js`**

In `app/static/js/app.js`, immediately before the final:

```javascript
document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
```

insert:

```javascript
function updateFilterChipSummary(chip) {
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

function initFilterChips(root, onChange) {
  root.querySelectorAll(".beasiswa-dash-filter-chip").forEach(function (chip) {
    chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) {
      cb.addEventListener("change", function () {
        updateFilterChipSummary(chip);
        onChange();
      });
    });
    const allBtn = chip.querySelector('[data-act="all"]');
    if (allBtn) {
      allBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) { cb.checked = true; });
        updateFilterChipSummary(chip);
        onChange();
      });
    }
    const noneBtn = chip.querySelector('[data-act="none"]');
    if (noneBtn) {
      noneBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        chip.querySelectorAll(".panel-opts input[type=checkbox]").forEach(function (cb) { cb.checked = false; });
        updateFilterChipSummary(chip);
        onChange();
      });
    }
    chip.addEventListener("click", function (e) {
      if (e.target.closest(".beasiswa-dash-filter-panel")) return;
      document.querySelectorAll(".beasiswa-dash-filter-chip.open").forEach(function (c) {
        if (c !== chip) c.classList.remove("open");
      });
      chip.classList.toggle("open");
    });
    updateFilterChipSummary(chip);
  });
}

document.addEventListener("click", function (e) {
  if (!e.target.closest(".beasiswa-dash-filter-chip")) {
    document.querySelectorAll(".beasiswa-dash-filter-chip.open").forEach(function (c) { c.classList.remove("open"); });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  initCommandPalette();
```

(The outside-click-to-close listener moves here from `dashboard_beasiswa.js` and is registered exactly once, at `app.js` load time — it already generically matches `.beasiswa-dash-filter-chip.open` anywhere in the document, so it covers Sahabat ETF's chips too once Task 2 adds them, with no duplicate listener registration.)

- [ ] **Step 4: Simplify `initDashboard()` to use the shared helper**

In `app/static/js/dashboard_beasiswa.js`, replace:

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

with:

```javascript
function initDashboard() {
  // Hanya inisialisasi satu kali
  if (window._dashInitialized) return;
  window._dashInitialized = true;

  initFilterChips(document, dashApplyFilters);
  dashApplyFilters();
}
```

- [ ] **Step 5: Run the test to verify it still passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v -k filter_chips_after_refactor`
Expected: PASS — the markup didn't change in this task, only the JS behind it.

- [ ] **Step 6: Run the full Beasiswa test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py tests/test_beasiswa_service.py -v`
Expected: all PASS.

- [ ] **Step 7: Manual check**

Open Beasiswa → Dashboard. Confirm the 4 filter chips (Tahun/Pillar/Program/Jenjang) still open/close, still filter correctly on checkbox change, and "Semua"/"Kosongkan" still work exactly as before this refactor.

- [ ] **Step 8: Commit**

```bash
cd C:\Financehub
git add app/static/js/app.js app/static/js/dashboard_beasiswa.js app/tests/test_beasiswa_routes.py
git commit -m "refactor: extract Dashboard's filter-chip wiring into a shared initFilterChips helper"
```

---

### Task 2: Convert Sahabat ETF's filters to chips

**Files:**
- Modify: `app/templates/sahabat_etf/_panel.html:20-52`
- Modify: `app/static/js/sahabat_etf.js:651-677`
- Test: `app/tests/test_beasiswa_routes.py`

**Interfaces:**
- Consumes: `initFilterChips`, `updateFilterChipSummary` (Task 1)

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_beasiswa_routes.py`:

```python
def test_sahabat_etf_filters_use_chip_pattern(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert resp.status_code == 200
    html = resp.data.decode()
    # The Sahabat ETF year/pillar filters should now render as chips...
    setf_section_start = html.index('id="tab-sahabat"')
    setf_section = html[setf_section_start:setf_section_start + 4000]
    assert "beasiswa-dash-filter-chip" in setf_section
    # ...and the old standalone "Pilih Semua" button should be gone.
    assert "setf-year-select-all" not in html
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v -k sahabat_etf_filters_use_chip_pattern`
Expected: FAIL — `setf-year-select-all` is still present, and the Sahabat ETF section has no `beasiswa-dash-filter-chip` yet.

- [ ] **Step 3: Convert the filter markup to chips**

In `app/templates/sahabat_etf/_panel.html`, replace:

```html
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
```

with:

```html
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

        <div class="filter-field">
          <label>Tahun Report (Export Laporan)</label>
          <select id="setf-report-year">
            {% for y in available_years|reverse %}
            <option value="{{ y }}">{{ y }}</option>
            {% endfor %}
          </select>
        </div>
      </div>
```

(`id="setf-filter-tahun"`/`id="setf-filter-pillar"` move onto the
`.panel-opts` div — same ids as before, so nothing else that might
reference them by id breaks; the `setf-year-cb`/`setf-pillar-cb` classes
`setfGetSelectedFilters()` reads are unchanged. The "Tahun Report" field
keeps its plain `.filter-field` wrapper, untouched.)

- [ ] **Step 4: Wire the chips via the shared helper**

In `app/static/js/sahabat_etf.js`, replace:

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

with:

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

(`initFilterChips(document, ...)` re-scans the *entire* document for
`.beasiswa-dash-filter-chip` each time it's called — calling it once from
`initDashboard()` and once from `initSahabatEtf()` means Dashboard's chips
briefly get re-wired a 2nd time if Sahabat ETF's tab is opened after
Dashboard's. This is harmless: each call only *adds* event listeners and
recomputes the same summary text; it doesn't remove or duplicate visible
behavior, since both `_dashInitialized`/`_sahabatInitialized` guards still
prevent either tab's own init from running more than once.)

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v -k sahabat_etf_filters_use_chip_pattern`
Expected: PASS

- [ ] **Step 6: Run the full Beasiswa test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v`
Expected: all PASS.

- [ ] **Step 7: Manual check**

Open Beasiswa → Sahabat ETF. Confirm Tahun and Pillar now render as chips
matching Dashboard's visual style. Click a chip, toggle a checkbox, confirm
the chip's summary text updates and the charts/tables re-filter. Click
"Semua"/"Kosongkan" inside the Tahun chip, confirm it selects/deselects all
years and re-filters. Confirm "Tahun Report (Export Laporan)" still works
unchanged.

- [ ] **Step 8: Commit**

```bash
cd C:\Financehub
git add app/templates/sahabat_etf/_panel.html app/static/js/sahabat_etf.js app/tests/test_beasiswa_routes.py
git commit -m "feat: convert Sahabat ETF Tahun/Pillar filters to Dashboard's chip style"
```

---

### Task 3: Remove the duplicate "Realisasi per Sahabat" table from Detail Tabel

**Files:**
- Modify: `app/templates/sahabat_etf/_panel.html:140-152`
- Test: `app/tests/test_beasiswa_routes.py`

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_beasiswa_routes.py`:

```python
def test_setf_family_table_and_chart_ids_appear_exactly_once(client):
    login(client)
    _select_etf(client)
    resp = client.get("/beasiswa/")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert html.count('id="setf-family-table"') == 1
    assert html.count('id="chart-keluarga"') == 1
    # The other Detail Tabel table must still be present.
    assert 'id="setf-table"' in html
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v -k setf_family_table_and_chart_ids_appear_exactly_once`
Expected: FAIL — both ids currently appear twice (`assert 2 == 1`).

- [ ] **Step 3: Delete the duplicate block**

In `app/templates/sahabat_etf/_panel.html`, inside the "Detail Tabel"
accordion, delete this entire block:

```html
      <div class="table-wrap">
        <h3>Realisasi per Sahabat</h3>
        <canvas id="chart-keluarga"></canvas>
        <div class="setf-compact-scroll">
          <table id="setf-family-table">
            <thead><tr><th>Sahabat</th><th>Nama</th><th class="num-right">Realisasi</th></tr></thead>
            <tbody><tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Memuat data...</td></tr></tbody>
          </table>
        </div>
      </div>

```

(The remaining content of that accordion — "Rincian Budget vs Realisasi
per Anggota", `id="setf-table"` — is untouched. The Grafik accordion's own
`chart-keluarga`/`setf-family-table` block, higher up in the same file, is
also untouched — that's the one copy that stays.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_beasiswa_routes.py -v -k setf_family_table_and_chart_ids_appear_exactly_once`
Expected: PASS

- [ ] **Step 5: Run the full test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/ -q`
Expected: same pass/fail counts as before this plan aside from the tests it added (pre-existing failures are documented as unrelated Windows SQLite file-lock flakiness in `01 - Proyek/FinanceHub/FinanceHub - Known Issues.md` in the Obsidian vault).

- [ ] **Step 6: Manual check**

Open Beasiswa → Sahabat ETF → Detail Tabel accordion. Confirm it now shows
only "Rincian Budget vs Realisasi per Anggota" with real data (no more
permanently-loading duplicate table above it). Scroll up to the Grafik
accordion and confirm "Realisasi per Sahabat" (chart + table) there still
renders correctly with data, unaffected by this removal.

- [ ] **Step 7: Commit**

```bash
cd C:\Financehub
git add app/templates/sahabat_etf/_panel.html app/tests/test_beasiswa_routes.py
git commit -m "fix: remove duplicate Realisasi-per-Sahabat table/chart that could never populate"
```

## Out of Scope

- Any change to `setf-table`'s own rendering logic — already correct.
- Any other tab's filter style.
- Any change to Dashboard's filter behavior — Task 1 is a pure refactor.
