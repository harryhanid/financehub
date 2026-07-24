# Design: Beasiswa Dashboard Filter Fix & Section Panels

**Date:** 2026-07-24
**Module:** Finance Hub — Sub Modul Beasiswa / Dashboard tab
**Status:** Approved

---

## Summary

Follow-up to the [Beasiswa Dashboard Card Redesign](2026-07-24-beasiswa-dashboard-card-redesign-design.md), which explicitly left the filter panel out of scope. Two problems reported by the user:

1. **Bug:** the Program and Jenjang Studi checkbox filters don't respond at all — toggling them does nothing, and their "Pilih Semua" buttons are broken after the tab's first load.
2. **Visual:** the filter bar looks inconsistent — Tahun/Pillar render as inline checkbox rows while Program/Jenjang render as separately-styled scrollable boxes with hardcoded colors that don't adapt to dark mode.

This design also restructures the Grafik section's 3 groups (Trend / Breakdown Realisasi / Detail Transaksi) from plain text-divider labels into visually distinct panels, per user feedback that the previous redesign's section labels were too subtle.

Both changes were validated with the user via visual mockups (3 options each) using the brainstorming skill's visual companion, before this spec was written.

---

## Root Cause (bug)

In `static/js/dashboard_beasiswa.js`, `initDashboard()` only attaches `change` listeners to `.dash-year-cb` and `.dash-pillar-cb`:

```js
document.querySelectorAll(".dash-year-cb").forEach(cb => cb.addEventListener("change", dashApplyFilters));
document.querySelectorAll(".dash-pillar-cb").forEach(cb => cb.addEventListener("change", dashApplyFilters));
```

`.dash-program-cb` and `.dash-jenjang-cb` checkboxes are read correctly by `dashGetSelectedFilters()` and sent correctly by `dashBuildQueryString()` — the backend support is complete — but nothing ever calls `dashApplyFilters()` when they change, so their state only takes effect as an accidental side-effect of some other filter changing.

The template's Program/Jenjang "Pilih Semua" buttons additionally call `loadDashboard()` (→ `initDashboard()`), which no-ops after first load due to the `if (window._dashInitialized) return;` guard — so those buttons do nothing at all post-load, unlike the Tahun "Pilih Semua" button which has its own dedicated listener calling `dashApplyFilters()` directly.

---

## Decisions

| Question | Decision |
|---|---|
| Filter bug fix scope | Fix by making listener-wiring generic (all filter checkboxes, not an enumerated subset) rather than patching the two missing calls — prevents the same class of bug if a 5th filter is added later |
| Filter visual direction | Replace all 4 filters (Tahun, Pillar, Program, Jenjang) with unified dropdown chips (Option A of 3 reviewed) — not a unified checkbox-box style, not a collapsible single-panel |
| Filter apply behavior | Live-apply on every checkbox toggle (matches current Tahun/Pillar behavior) — decided by assistant, not explicitly asked, since it's the established pattern already in use |
| Filter dropdown close behavior | Stays open until user clicks outside the panel — standard multi-select combo pattern, lets the user toggle several options without reopening each time |
| "Pilih Semua" / "Kosongkan" | Added to all 4 filter dropdowns for consistency (today only Tahun and Program/Jenjang have "Pilih Semua"; Pillar has none) |
| Card layout direction | Wrap each of the 3 existing chart-card groups in a distinct section panel (tinted background + accent-color title, Option A of 3 reviewed) — not a hero+bento layout, not sub-tabbed sections |
| Color source | All new styling uses existing CSS custom properties (`--card`, `--border`, `--text`, `--text-muted`, `--primary`, `--accent-surface`) instead of hardcoded hex — fixes the dark-mode-blindness that was part of the "jelek" (ugly) complaint on the current filter bar |
| Blast radius | New/changed classes live only in `beasiswa_dashboard.css` and are only referenced from `beasiswa/index.html` + `dashboard_beasiswa.js`, consistent with the prior redesign's isolation |

---

## Architecture

### File changes

- **Modify:** `app/static/css/beasiswa_dashboard.css` — add filter-chip/dropdown classes and section-panel classes; remove `.beasiswa-dash-section-label` (superseded).
- **Modify:** `app/templates/beasiswa/index.html` — replace the filter-bar markup (lines ~54–104) with the 4-chip structure; restructure the Grafik grid (lines ~113–178) so each of the 3 groups is wrapped in its own `.beasiswa-dash-section-panel`, replacing the 2 standalone `.beasiswa-dash-section-label` divs.
- **Modify:** `app/static/js/dashboard_beasiswa.js` — rewrite `initDashboard()`'s listener wiring to be generic across all filter checkboxes; add dropdown open/close toggle logic; add "Pilih Semua"/"Kosongkan" handlers per dropdown. `dashGetSelectedFilters()`, `dashBuildQueryString()`, `dashApplyFilters()`, and every chart/table render function are unchanged.

No Python/backend changes. No changes to any other template or to the 3 other consumers of the pre-existing shared classes (Sahabat ETF, Budget Monitoring dashboard, and this same file's own summary-card tint classes from the prior redesign).

### Filter bar markup (new shape)

```html
<div class="beasiswa-dash-filterbar">
  <div class="beasiswa-dash-filter-chip" data-filter="tahun">
    <span class="lbl">Tahun</span>
    <span class="val">4 dipilih</span>
    <span class="caret">▾</span>
    <div class="beasiswa-dash-filter-panel">
      <div class="panel-head"><button data-act="all">Semua</button><button data-act="none">Kosongkan</button></div>
      <div class="panel-opts">
        <!-- existing .dash-year-cb checkboxes, unchanged id/class -->
      </div>
    </div>
  </div>
  <!-- same structure repeated for pillar, program, jenjang -->
</div>
```

Existing checkbox `id`s/classes (`dash-year-cb`, `dash-pillar-cb`, `dash-program-cb`, `dash-jenjang-cb`) and the `dash-filter-tahun` / `dash-filter-pillar` / `dash-filter-program` / `dash-filter-jenjang` container IDs are preserved inside the new `panel-opts` wrapper — `dashGetSelectedFilters()` needs zero changes.

### New CSS classes (in `beasiswa_dashboard.css`)

```css
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
  border-radius: var(--r-md, 8px);
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
  border-radius: var(--r-md, 8px);
  box-shadow: 0 4px 14px rgba(0,0,0,.12);
  padding: 0.6rem;
  min-width: 200px;
}
.beasiswa-dash-filter-chip.open .beasiswa-dash-filter-panel { display: block; }
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

/* Section panels — replaces .beasiswa-dash-section-label */
.beasiswa-dash-section-panel {
  background: color-mix(in srgb, var(--primary) 5%, transparent);
  border: 1px solid var(--border);
  border-radius: var(--r-lg, 10px);
  padding: 0.8rem;
  margin-bottom: 0.7rem;
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
```

`.beasiswa-dash-grafik-grid` (existing, from the prior redesign) is unchanged in definition but now nests *inside* each `.beasiswa-dash-section-panel` instead of being one grid for all 9 cards.

### JS changes (`dashboard_beasiswa.js`)

`initDashboard()` rewritten to wire listeners generically:

```js
function initDashboard() {
  if (window._dashInitialized) return;
  window._dashInitialized = true;

  document.querySelectorAll('.beasiswa-dash-filter-chip').forEach(function (chip) {
    document.querySelectorAll('.panel-opts input[type=checkbox]', chip).forEach(function (cb) {
      cb.addEventListener('change', dashApplyFilters);
    });
    chip.querySelector('[data-act="all"]')?.addEventListener('click', function (e) {
      e.stopPropagation();
      chip.querySelectorAll('.panel-opts input[type=checkbox]').forEach(cb => cb.checked = true);
      dashApplyFilters();
    });
    chip.querySelector('[data-act="none"]')?.addEventListener('click', function (e) {
      e.stopPropagation();
      chip.querySelectorAll('.panel-opts input[type=checkbox]').forEach(cb => cb.checked = false);
      dashApplyFilters();
    });
    chip.addEventListener('click', function (e) {
      if (e.target.closest('.beasiswa-dash-filter-panel')) return; // don't toggle when clicking inside panel
      document.querySelectorAll('.beasiswa-dash-filter-chip.open').forEach(c => { if (c !== chip) c.classList.remove('open'); });
      chip.classList.toggle('open');
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.beasiswa-dash-filter-chip')) {
      document.querySelectorAll('.beasiswa-dash-filter-chip.open').forEach(c => c.classList.remove('open'));
    }
  });

  dashApplyFilters();
}
```

A small chip-summary updater (`dashUpdateChipSummary(chip)`, called from `dashApplyFilters()` or inline in each checkbox handler) refreshes each chip's `.val` text after any change — new, small function, not present today since the old UI had no collapsed-summary state to keep in sync. Exact text logic, by count of checked boxes vs. total in that panel:

- All checked → `"Semua"`
- None checked → `"Tidak ada"` (styled muted/warning — this is a valid but probably-unintended state, e.g. user cleared Program filter entirely, which the existing backend already handles as "no filter on this dimension" per `dashBuildQueryString()`'s `if (filters.programs.length)` guard, not as "show nothing")
- Otherwise → `"{n} dipilih"` where `{n}` is the checked count

`dashGetSelectedFilters()`, `dashBuildQueryString()`, `dashApplyFilters()`, and all `dashRender*` functions: **unchanged**.

### Grafik section restructuring

The existing 3 groupings (unchanged from the prior redesign) each become their own panel:

1. **Trend** — Trend per Bulan, Trend per Tahun, Perbandingan Realisasi per Bulan per Tahun
2. **Breakdown Realisasi** — Realisasi per Kategori (chart + table), Realisasi per Jenjang Studi, Realisasi per Pillar per Tahun
3. **Detail Transaksi** — 20 Transaksi Terakhir, Rincian Budget vs Realisasi per Program

No chart/table `id`s, canvas elements, or JS render targets move or change — only their HTML ancestor structure (which panel wraps them) changes.

---

## Testing

Same no-frontend-framework verification pattern as the prior redesign:

- App-boot sanity check.
- Force-render `/beasiswa/` via Flask test client with a real login (test DB) — 200 OK, no Jinja error, and assert the new filter-chip/section-panel classes are present in the response body while the old `.beasiswa-dash-section-label` class is gone.
- Structural grep-check on `dashboard_beasiswa.js`: `initDashboard` no longer references `.dash-year-cb`/`.dash-pillar-cb` by name (confirms the generic-wiring fix actually replaced the old enumerated version, not just added to it).
- Manual functional check (if a preview session with real data is available, and not against the shared live production DB — see prior-session caution): toggle a Program checkbox and confirm the dashboard data changes; toggle a Jenjang checkbox and confirm the same.
- Full Python regression suite run once at the end as a standard sanity check — no backend logic changes in this task, so no new failures expected beyond whatever pre-existing/unrelated failures are already known.

## Out of Scope

- Any change to the `/beasiswa/api/dashboard/*` backend endpoints — the bug is entirely frontend event-wiring, backend already supports program/jenjang filtering correctly.
- Mobile/narrow-viewport-specific redesign beyond existing `flex-wrap` responsiveness already present in the filter bar.
- Changing which 9 cards exist, what data they show, or their internal chart/table rendering logic.
- Rewiring the summary stat-card tint system from the prior redesign — untouched.
