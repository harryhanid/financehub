# Sahabat ETF — Filter Style Unification & Duplicate Table Fix — Design

## Problem

Two separate issues on Beasiswa → Sahabat ETF (`templates/sahabat_etf/_panel.html`):

**1. Filter style predates Dashboard's redesign.** Beasiswa's Dashboard tab
(`beasiswa/index.html:39-107`) uses a dropdown-chip filter pattern (label +
summary + caret, click to open a checkbox panel with "Semua"/"Kosongkan"
buttons) — the result of the 2026-07-24 filter redesign. Sahabat ETF's
Tahun/Pillar filters (`_panel.html:20-43`) still use the older style: every
checkbox always visible inline, plus a standalone "Pilih Semua" button next
to the Tahun label. Visually and behaviorally inconsistent with the tab
right next to it.

**2. "Realisasi per Sahabat" table in the Detail Tabel section never
populates.** `id="setf-family-table"` and `id="chart-keluarga"` each appear
**twice** in `_panel.html`:

| Location | Line | Columns |
|---|---|---|
| "Grafik" accordion | 96-105 | Sahabat, Nama, Kategori Realisasi, Realisasi (4 cols) |
| "Detail Tabel" accordion | 144-151 | Sahabat, Nama, Realisasi (3 cols) |

`sahabat_etf.js` targets both ids via `document.querySelector("#setf-family-table tbody")` (lines 239, 602) and `setfRenderStackedBarChart("chart-keluarga", ...)` (line 609) — `querySelector`/`getElementById` always resolve to the *first* matching element in DOM order, so every render call fills the Grafik-accordion copy; the Detail Tabel copy is permanently stuck on its "Memuat data..." placeholder. It's a near-exact duplicate of the Grafik version (missing one column) — almost certainly a copy-paste leftover, not an intentionally separate second view.

The Detail Tabel accordion's other table, "Rincian Budget vs Realisasi per Anggota" (`id="setf-table"`, unique, wired via `setfRenderTable()` at `sahabat_etf.js:370`), is unaffected and out of scope.

## Decisions (confirmed with user)

- Remove the duplicate "Realisasi per Sahabat" table+chart from the Detail Tabel accordion entirely — the Grafik accordion's copy (which already has one more column) is the only one kept.
- Filter chips are extracted into a shared, generic helper (`initFilterChips`) reused by both Dashboard and Sahabat ETF, rather than duplicating the chip-wiring JS a second time — the exact kind of duplication already responsible for problem #2 above.

## Design

### Extract `initFilterChips(root, onChange)` into `app.js`

`initDashboard()`'s chip-wiring loop (`dashboard_beasiswa.js:491-524`) and
`dashUpdateChipSummary()` (`dashboard_beasiswa.js:472-484`) are already fully
generic — neither references anything Dashboard-specific except the
`dashApplyFilters()` call at the end of each event handler. Both move to
`app.js` as:

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
```

The outside-click-to-close listener is registered once at `app.js` load
time (not inside `initFilterChips`, so calling it twice — once for
Dashboard's chips, once for Sahabat ETF's — never double-registers it); it
already generically matches any `.beasiswa-dash-filter-chip.open` regardless
of which tab/module created it.

`dashboard_beasiswa.js`'s `initDashboard()` (lines 486-533) drops its own
copy of this loop and `dashUpdateChipSummary()`, replacing them with a
single call: `initFilterChips(document, dashApplyFilters);`.

### Convert Sahabat ETF's Tahun/Pillar filters to chips

Replace `_panel.html:20-43`'s inline-checkbox markup with the same
structure Dashboard uses per chip (label/val/caret trigger +
panel/panel-head/panel-opts), just swapping the checkbox class names
(`setf-year-cb`/`setf-pillar-cb`, already read by `setfGetSelectedFilters()`
— unchanged) and ids (`setf-filter-tahun`/`setf-filter-pillar`, already
used by the Jinja loops that populate each list — unchanged). The
standalone "Pilih Semua" button (`setf-year-select-all`) is removed — its
job is now the Tahun chip's own "Semua" button, exactly like Dashboard's
Tahun chip.

`initSahabatEtf()` (`sahabat_etf.js:651-677`) drops its manual
`.setf-year-cb`/`.setf-pillar-cb`/`setf-year-select-all` wiring (lines
658-670), replacing it with `initFilterChips(document, setfApplyFilters);`.
The "Tahun Report (Export Laporan)" `<select>` and its own change listener
(lines 671-675) are untouched — a separate export-parameter control, not a
data filter.

### Remove the duplicate table/chart from Detail Tabel

In `_panel.html`, delete this block from the "Detail Tabel" accordion
(lines 144-152):

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

The Grafik accordion's copy (same ids, one more column, already correctly
populated) is untouched. The Detail Tabel accordion keeps only "Rincian
Budget vs Realisasi per Anggota" (`setf-table`) after this removal.

## Testing

- No frontend test framework exists in this codebase for chip/DOM behavior
  (consistent precedent — every prior UI-only fix this session relied on
  route-level smoke tests plus manual verification).
- Route-level smoke test: `GET /beasiswa/?tab=sahabat` (or however this
  panel is server-rendered) returns 200, response contains exactly one
  `id="setf-family-table"` occurrence (not two) and exactly one
  `id="chart-keluarga"` occurrence.
- Route-level smoke test: the Sahabat ETF filter markup contains
  `beasiswa-dash-filter-chip` (confirms the chip conversion landed) and no
  longer contains `setf-year-select-all`.
- Manual: open Beasiswa → Sahabat ETF, confirm Tahun/Pillar render as
  chips matching Dashboard's visual style; click a chip, toggle checkboxes,
  confirm the summary text and chart/table data update; confirm the
  Detail Tabel accordion now shows only "Rincian Budget vs Realisasi per
  Anggota" (no more permanently-loading duplicate). Switch to Dashboard tab
  and confirm its own chips still work identically to before (regression
  check on the extraction).

## Out of Scope

- The "Tahun Report (Export Laporan)" export-parameter dropdown.
- "Rincian Budget vs Realisasi per Anggota" (`setf-table`) — already
  correctly wired, not touched.
- Any change to Dashboard's own filter *behavior* — only its implementation
  moves (into a shared, reusable function), output is identical.
- Any other tab's filter style (Data Siswa, Data Budget, etc.) — this spec
  covers Sahabat ETF only, matching what was reported.
