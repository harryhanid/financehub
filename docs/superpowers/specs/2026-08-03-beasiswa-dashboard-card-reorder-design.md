# Design: Beasiswa Dashboard Card Reorder & Tidy-Up

**Date:** 2026-08-03
**Module:** Finance Hub — Sub Modul Beasiswa / Dashboard tab
**Status:** Approved

---

## Summary

Follow-up to the [Card Redesign](2026-07-24-beasiswa-dashboard-card-redesign-design.md) and [Filter Fix & Section Panels](2026-07-24-beasiswa-dashboard-filter-fix-and-section-panels-design.md) designs, which grouped the Dashboard tab's 9 chart/table cards into 3 section panels (Trend, Breakdown Realisasi, Detail Transaksi) but left card order and sizing as-is.

Two problems identified during this review:

1. **Uneven proportions:** chart cards (canvas, ~260-300px natural height) and compact table cards (height follows content) sit in the same CSS grid row within a panel, so rows don't align — 2 chart cards + 1 table card share a row in Trend; 1 chart card + 3 table cards share a row in Breakdown Realisasi.
2. **Misplaced card:** "Rincian Budget vs Realisasi per Program" lives in the Detail Transaksi panel, but it's a breakdown-by-dimension card (Program) — semantically the same kind of card as Kategori/Jenjang/Pillar, which all live in Breakdown Realisasi. Detail Transaksi is meant for raw/row-level transaction data ("20 Transaksi Terakhir"), not another aggregate breakdown.

## Decisions

| Question | Decision |
|---|---|
| Fix uneven proportions | Split each panel's single mixed grid into two sequential grids — a "chart row" (chart-type cards only) and a "table row" (compact/table-type cards only) — using the existing `.beasiswa-dash-grafik-grid` class unchanged. No new CSS. |
| Fix misplaced card | Move "Rincian Budget vs Realisasi per Program" from Detail Transaksi into Breakdown Realisasi's table row (4th breakdown dimension alongside Kategori/Jenjang/Pillar) |
| Detail Transaksi panel after the move | Stays a separate panel with its one remaining card ("20 Transaksi Terakhir") — kept distinct because it serves a different purpose (raw recent transactions vs. aggregate breakdowns), not merged into Breakdown Realisasi |
| Sizing CSS | No new classes, no new sizing rules — same `.beasiswa-dash-grafik-grid` / `.beasiswa-dash-chart-card` / `.compact` classes as today, just re-grouped in markup |
| Card content/behavior | Unchanged — no chart/table `id`s, canvas elements, or JS render targets move or change, only their HTML ancestor position |
| Two insights raised during discussion (custom `max-height` on "20 Transaksi Terakhir"; no % budget-used indicator on the Sisa Budget summary card) | Explicitly out of scope — noted for a possible future pass, not part of this change |

---

## Architecture

### File changes

- **Modify:** `app/templates/beasiswa/index.html` (Grafik section, currently ~lines 113–202) — restructure the 3 panels' internal markup per the new grouping below. No other file changes: `app/static/css/beasiswa_dashboard.css` and `app/static/js/dashboard_beasiswa.js` are untouched.

### New card grouping and order

**Trend panel:**
- Chart row (`.beasiswa-dash-grafik-grid`): Trend per Bulan, Trend per Tahun
- Table row (`.beasiswa-dash-grafik-grid`): Perbandingan Realisasi per Bulan per Tahun

**Breakdown Realisasi panel:**
- Chart row (`.beasiswa-dash-grafik-grid`): Realisasi per Kategori (chart)
- Table row (`.beasiswa-dash-grafik-grid`): Realisasi per Kategori (Tabel), Realisasi per Jenjang Studi, Realisasi per Pillar per Tahun, Rincian Budget vs Realisasi per Program

**Detail Transaksi panel:**
- Table row (`.beasiswa-dash-grafik-grid`): 20 Transaksi Terakhir

Each panel keeps its existing `.beasiswa-dash-section-panel` wrapper and `.beasiswa-dash-section-title` label (unchanged: "Trend", "Breakdown Realisasi", "Detail Transaksi") — only the grid(s) inside each panel change, from one mixed grid to one or two type-grouped grids in sequence.

No `id` attributes, canvas elements, table `id`s, or any JS-side `dashRender*` function changes — every card keeps its exact existing markup, just relocated as a whole `<div class="beasiswa-dash-chart-card">...</div>` block to its new position.

---

## Testing

Same no-frontend-framework verification pattern as the two prior Dashboard redesigns:

- App-boot sanity check (`python -c "from app import create_app; create_app()"`).
- Force-render `/beasiswa/` via Flask test client with a real login (test DB) — 200 OK, no Jinja error.
- Grep-check: all 9 existing card `id`s (`dash-chart-bulanan`, `dash-chart-tahunan`, `dash-monthly-table`, `dash-chart-kategori`, `dash-kategori-table`, `dash-jenjang-table`, `dash-pillar-year-table`, `dash-latest-payments-table`, `dash-program-table`) are still present exactly once each in `beasiswa/index.html` after the move — confirms nothing was duplicated or dropped during the markup restructure.
- Manual browser check if a preview session with real data is available (and not against the shared live/production DB); skip if not — visually confirm chart-row cards sit in one aligned row and table-row cards sit in another, per panel.
- Full Python regression suite run once at the end as a standard sanity check — not expected to reveal anything, since no backend or JS logic changes in this task.

## Out of Scope

- Any CSS/sizing changes — this is a pure markup reorder, reusing existing classes exactly as they render today.
- The two insights raised during discussion (custom `max-height` normalization on "20 Transaksi Terakhir"; a % budget-used indicator on the Sisa Budget summary card).
- The summary stat cards (Total Siswa Aktif / Budget / Klaim / Realisasi / Sisa Budget) — order and styling untouched.
- The filter bar (Tahun/Pillar/Program/Jenjang Studi chips) — untouched.
- Changing which 9 cards exist or what data they show — this is a position-only reorder.
