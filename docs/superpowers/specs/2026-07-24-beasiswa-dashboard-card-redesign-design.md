# Design: Beasiswa Dashboard Card Redesign

**Date:** 2026-07-24
**Module:** Finance Hub — Sub Modul Beasiswa / Dashboard tab
**Status:** Approved

---

## Summary

The Beasiswa Dashboard tab (`/beasiswa/`) is visually generic — its summary stat cards and 9 chart/table cards reuse `.budget-stat-card` / `.budget-chart-card` / `.budget-summary-grid` classes defined in `budget.css`, which are also consumed by two other pages (Sahabat ETF, Budget Monitoring dashboard). This redesign gives the Beasiswa Dashboard its own visual identity — tint-coded summary cards and grouped, uncluttered chart cards — without touching the shared classes or the other two pages that use them.

Alongside this, a real bug was found and fixed during investigation: `get_dashboard_monthly()` (backing the "Trend per Bulan" chart) unconditionally raised `UnboundLocalError` on every call (variables used before assignment, plus a non-f-string with unsubstituted `{program_sql}{jenjang_sql}` placeholders). That fix already landed in the working tree, verified by a new test (`test_get_dashboard_monthly_does_not_crash_and_applies_program_filter`), and is not part of this redesign's scope — noted here only because it's why the chart was rendering empty.

---

## Decisions

| Question | Decision |
|---|---|
| Redesign scope | Whole Dashboard tab (stat cards + chart cards), not just the 5 summary cards |
| Visual direction | Light theme, more intentional/"premium" than generic — not dark/glassmorphism, not a copy of any other module |
| Reference page | Sahabat ETF was proposed as a visual reference but turned out to use the exact same generic classes — no genuinely more-polished existing page to draw from, so this design originates fresh from existing design tokens |
| Blast radius | New page-specific classes only. Sahabat ETF and Budget Monitoring dashboard (both consumers of the same shared classes) are untouched |
| CSS file location | New dedicated file `app/static/css/beasiswa_dashboard.css`, linked only from `templates/beasiswa/index.html` — not added to the already-overloaded, confusingly-named `budget.css` |
| Summary card style | Tint-per-semantic background (Option C from visual review): each of the 5 stat cards gets a background tint matching what it represents |
| Chart card style | Neutral/uniform cards (no per-card color coding), grouped under 3 section labels for information hierarchy (Option C from visual review) |
| Filter panel | Out of scope — not part of what was requested, left as-is |

---

## Architecture

### File changes

- **Create:** `app/static/css/beasiswa_dashboard.css` — all new classes for this redesign live here.
- **Modify:** `app/templates/beasiswa/index.html` — link the new stylesheet; replace `.budget-summary-grid` / `.budget-chart-card` / `.setf-grafik-grid` class references with the new `beasiswa-dash-*` equivalents on the static markup (filter panel wrapper, Grafik section grid, the 9 static `<div class="budget-chart-card">...</div>` blocks); insert 2 new `<div class="beasiswa-dash-section-label">` elements to split the 9 cards into 3 visual groups.
- **Modify:** `app/static/js/dashboard_beasiswa.js` — `dashRenderSummaryCards()` and `dashRenderSummarySkeleton()` currently generate `'<div class="budget-stat-card' + c[2] + '">...'` HTML strings; update the class name and the per-metric modifier logic to emit the new tint classes instead.

No other files change. No Python/backend changes. No changes to any other template.

### New CSS classes (in `beasiswa_dashboard.css`)

```css
/* Layout containers */
.beasiswa-dash-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.beasiswa-dash-grafik-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

/* Section grouping labels inside the grafik grid */
.beasiswa-dash-section-label {
  grid-column: 1 / -1;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94a3b8;
  margin: 0.6rem 0 0.1rem;
  padding-top: 0.4rem;
  border-top: 1px solid #f1f5f9;
}
.beasiswa-dash-section-label:first-child {
  border-top: none;
  padding-top: 0;
  margin-top: 0;
}

/* Summary stat cards — base + tint modifiers */
.beasiswa-dash-stat-card {
  border-radius: 10px;
  padding: 1rem 1.1rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.beasiswa-dash-stat-card .label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  font-weight: 600;
}
.beasiswa-dash-stat-card .value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  margin-top: 0.25rem;
}

.beasiswa-dash-stat-card.tint-budget   { background: #eff6ff; border-color: #bfdbfe; }
.beasiswa-dash-stat-card.tint-budget   .value { color: #1d4ed8; }
.beasiswa-dash-stat-card.tint-klaim    { background: #fffbeb; border-color: #fde68a; }
.beasiswa-dash-stat-card.tint-klaim    .value { color: #b45309; }
.beasiswa-dash-stat-card.tint-realisasi { background: #f0fdf4; border-color: #bbf7d0; }
.beasiswa-dash-stat-card.tint-realisasi .value { color: #15803d; }
.beasiswa-dash-stat-card.tint-negative { background: #fef2f2; border-color: #fecaca; }
.beasiswa-dash-stat-card.tint-negative .value { color: #b91c1c; }

/* Chart/table cards — neutral, uniform */
.beasiswa-dash-chart-card {
  background: #fff;
  border-radius: 10px;
  padding: 1rem;
  border-top: 3px solid #e2e8f0;
  box-shadow: 0 1px 2px rgba(15,23,42,.05);
}
.beasiswa-dash-chart-card canvas { max-height: 260px; }
.beasiswa-dash-chart-card.compact { /* mirrors existing .setf-compact-card sizing */ }
```

Exact spacing/sizing values for `.compact` and any responsive breakpoints are carried over unchanged from the existing `.setf-compact-card` / `.setf-grafik-grid` responsive rules in `budget.css` (copied into the new file, not referenced across files, to keep `beasiswa_dashboard.css` self-contained).

### Summary card tint mapping

| Card | Class modifier |
|---|---|
| Total Siswa Aktif | *(base, no modifier)* |
| Total Budget | `.tint-budget` |
| Total Klaim | `.tint-klaim` |
| Total Realisasi | `.tint-realisasi` |
| Sisa Budget | `.tint-negative` **only when negative** (mirrors today's `setf-sisa-negative` conditional logic — positive Sisa Budget stays base/neutral) |

`dashRenderSummaryCards()`'s existing `cards` array (list of `[label, value, modifierSuffix]` tuples) already has a per-card modifier slot (currently `" setf-stat-realisasi"` / `" setf-sisa-negative"` / `""`) — this task changes only the modifier strings and the base class name, not the array's shape or the function's control flow.

### Chart card grouping

The 9 existing `<div class="budget-chart-card">` blocks in `beasiswa/index.html` (lines ~113–178) split into 3 groups via 2 new section-label `<div>`s inserted between them — no change to which cards exist, their IDs, or their JS-side rendering logic:

1. **Trend** — Trend per Bulan, Trend per Tahun, Perbandingan Realisasi per Bulan per Tahun
2. **Breakdown Realisasi** — Realisasi per Kategori (chart + table), Realisasi per Jenjang Studi, Realisasi per Pillar per Tahun
3. **Detail Transaksi** — 20 Transaksi Terakhir, Rincian Budget vs Realisasi per Program

---

## Testing

No frontend test framework exists in this codebase (confirmed pattern from prior sessions). Verification:

- App-boot sanity check (`python -c "from app import create_app; create_app()"`).
- Force-render `/beasiswa/` via Flask test client — 200 OK, no Jinja error.
- Grep-check: zero remaining references to `.budget-stat-card` / `.budget-chart-card` / `.budget-summary-grid` / `.setf-grafik-grid` inside `beasiswa/index.html` and `dashboard_beasiswa.js` after migration (catches any missed rename).
- Grep-check: `.budget-stat-card` / `.budget-chart-card` / `.budget-summary-grid` usages in `sahabat_etf/index.html` and `budget/dashboard.html` are unchanged (byte-identical) — proves zero blast radius.
- Manual browser check if a preview session is available; skip if not (server connects to a live/shared environment, matching prior-session caution around that).
- Full Python regression suite run once at the end as a standard sanity check — not expected to reveal anything, since no backend logic changes in this task.

## Out of Scope

- The filter panel (Tahun/Pillar/Program/Jenjang Studi checkboxes) — not part of what was requested.
- `get_dashboard_monthly()`'s bug fix — already done separately, unrelated to this redesign.
- Upgrading the shared `.budget-*` classes for Sahabat ETF or Budget Monitoring — explicitly rejected due to blast radius (see Decisions table).
- Restructuring what data each chart/table shows — this is a visual-only pass, not an information-architecture rework beyond the 3-group labeling.
