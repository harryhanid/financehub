# Design: Sahabat ETF Tab Integration into Beasiswa

**Date:** 2026-07-24
**Module:** Finance Hub — Sub Modul Beasiswa
**Status:** Approved

---

## Summary

The "Sahabat ETF" entry in the Beasiswa page's tab bar is currently a real hyperlink (`<a href="/beasiswa/sahabat">`) styled to look like a tab button but performing a full page navigation to a separate standalone page (its own Flask blueprint, its own `{% extends "base.html" %}` template, its own JS file). Every other tab (Dashboard, Data Siswa, Data Budget, Data Payment, Report Siswa, Rekam Medis) is a real `.tab-panel` that stays on the same page — clicking between them is instant, client-side, and the tab bar itself never disappears.

User request: make Sahabat ETF behave like the other 6 tabs, so switching between any of the 7 feels the same — no page reload, tab bar always visible.

This redesign embeds Sahabat ETF as a real 7th `.tab-panel` inside `beasiswa/index.html`, following the exact pattern already used by every other tab on that page: the tab's HTML shell is server-rendered inline when `/beasiswa/` loads, and its data is lazy-fetched via JS only when the tab is first clicked (mirroring `loadDashboard()` → `initDashboard()`).

---

## Decisions

| Question | Decision |
|---|---|
| Embedding mechanism | Server-rendered Jinja partial included inline in `beasiswa/index.html` at page load (matching every other tab), NOT an AJAX-fetched HTML fragment. Only the *data* (charts, tables) is lazy-fetched client-side, same as the Dashboard tab today. |
| Non-ETF company behavior | Tab stays visible; its panel shows the existing "Ganti Company" notice instead of dashboard content — identical to today's behavior, just relocated. No conditional tab-hiding. |
| Old URL `/beasiswa/sahabat` | Redirects (302) to `/beasiswa/?tab=sahabat`, which auto-selects the Sahabat ETF tab on load instead of defaulting to Dashboard. Bookmarks/shared links keep working. |
| `/beasiswa/sahabat/api/*` and `/export/*` routes | Untouched — these are independent JSON/CSV/XLSX endpoints triggered by `fetch()`/`window.location.href`/`window.print()`, unaffected by which page embeds the triggering UI. |
| `etf_company_required` guard on those routes | Untouched — stays as backend defense-in-depth, independent of the HTML-level `wrong_company` notice. |
| Shared `initTabs()` (used by 3 pages: `bank/index.html`, `beasiswa/index.html`, `payment_memo/index.html`) | Extended to read a `?tab=` query param and click the matching `[data-tab]` button on load, falling back to today's behavior (click the first tab) when the param is absent or doesn't match. Confirmed zero collision: none of the 3 `[data-tabs]`-wrapped pages currently use `?tab=` for anything else. (ETF Payment Application also uses a `?tab=` param, but for an entirely separate, non-`[data-tabs]` radio-button tab system — unaffected.) |

---

## Architecture

### File changes

1. **Create `templates/sahabat_etf/_panel.html`** — extract the inner content currently in `sahabat_etf/index.html`'s `{% block content %}` (everything from `{% if wrong_company %}...{% else %}...{% endif %}`, i.e. the "Ganti Company" notice and the full dashboard markup) into this new partial. No behavior change to the markup itself — pure extraction.

2. **Modify `templates/sahabat_etf/index.html`** — becomes a thin wrapper: keeps `{% extends "base.html" %}`, the `<link>`/`<script>` head block (Chart.js etc.), and `{% include "sahabat_etf/_panel.html" %}` in place of the extracted content. Still renders as a standalone page for any internal/direct use, but the primary entry point (see #5) no longer routes here.

3. **Modify `modules/beasiswa/routes.py`** — the `/beasiswa/` `index()` route additionally computes what the partial needs: `wrong_company` (`session.get("company_code") != "ETF"`), `available_years`, `available_pillars` (via the existing `get_available_years`/`get_available_pillars` functions already imported by `modules/sahabat_etf/routes.py` — import them here too, or call through `modules.sahabat_etf.service` directly), and passes them to `render_template`.

4. **Modify `templates/beasiswa/index.html`** —
   - Add a 7th tab button inside the existing `<div class="tabs">` block (removing the current standalone `<a class="tab-btn" href="/beasiswa/sahabat">` link): `<button class="tab-btn" data-tab="tab-sahabat" onclick="loadSahabatETF()">Sahabat ETF</button>`.
   - Add the panel: `<div class="tab-panel" id="tab-sahabat">{% include "sahabat_etf/_panel.html" %}</div>` — needs the same `budget.css` and Chart.js/datalabels `<script>` tags the partial's charts depend on; `beasiswa/index.html` already loads all three (confirmed: it loads `budget.css` and both Chart.js CDN scripts for its own Dashboard tab), so no new head-block additions needed.

5. **Modify `modules/sahabat_etf/routes.py`** — the `@bp.route("/")` `index()` view changes from rendering the full page to `return redirect(url_for("beasiswa.index", tab="sahabat"))`. All other routes (`/api/*`, `/export/*`) are untouched.

6. **Modify `static/js/sahabat_etf.js`** — `initSahabatEtf()` already exists as a named function (called today via `document.addEventListener("DOMContentLoaded", initSahabatEtf)` in the standalone template) and needs no renaming. Add an idempotency guard at its top, the same pattern `initDashboard()` already uses: `if (window._sahabatInitialized) return; window._sahabatInitialized = true;`. The new tab button's `onclick` calls `initSahabatEtf()` directly. The standalone `sahabat_etf/index.html` wrapper keeps its existing `DOMContentLoaded` call to the same function — with the guard added, calling it that way still works unchanged for standalone/direct access.

7. **Modify `templates/beasiswa/index.html` scripts block** — add `<script src="{{ url_for('static', filename='js/sahabat_etf.js') }}"></script>`. Today only the standalone `sahabat_etf/index.html` loads this file; once embedded, `beasiswa/index.html` must load it too (`initSahabatEtf` and its helper functions — `setfApplyFilters`, `setfExportPdf`, etc. — must exist in the page's JS scope before the tab button's `onclick` can call them).

### Known risk: DOM id collisions

Sahabat ETF's table/filter ids consistently use a `setf-` prefix (`setf-summary`, `setf-year-cb`, `setf-monthly-table`, ...), but its **canvas ids do not** (`chart-bulanan`, `chart-tahunan`, `chart-keluarga`, `chart-kategori` — no prefix). Spot-checked against the Beasiswa Dashboard tab (which uses `dash-`-prefixed canvas ids: `dash-chart-bulanan`, `dash-chart-tahunan`) — no collision there. But this was a spot-check, not an exhaustive cross-reference against all 6 other tabs' ids. The implementation plan must grep every `id="..."` in the extracted partial and confirm none collide with any id already present elsewhere in `beasiswa/index.html` before considering the embed complete — an id collision would make `getElementById`/`querySelector` calls (from either tab's JS) silently resolve to the wrong element instead of erroring, which force-render/structural checks won't catch.

### Pre-existing bug found during investigation (not in scope, noted for the record)

Within `sahabat_etf/index.html` itself (independent of this integration), `id="chart-keluarga"` and `id="setf-family-table"` each appear **twice** — once inside the "Grafik" section (current lines ~104–113) and again inside the separate "Detail Tabel" section (current lines ~152–159). Duplicate ids mean `getElementById` always resolves to the first occurrence, so the "Detail Tabel" section's own family chart/table are dead — permanently showing whatever the Grafik section's version renders into the *first* matching element, never their own. This bug is carried over unchanged by this integration (the partial extraction is a verbatim copy) — it belongs to the still-uncommitted Sahabat ETF Dashboard BI feature this integration is embedding, not to this task. Flagging here so it isn't mistaken for something this integration introduced.

7. **Modify `static/js/app.js`** — `initTabs(container)`'s final line, currently unconditional:
   ```js
   if (tabs.length > 0) tabs[0].click();
   ```
   becomes:
   ```js
   const requestedTab = new URLSearchParams(window.location.search).get("tab");
   const requested = requestedTab && container.querySelector(`[data-tab="tab-${requestedTab}"]`);
   if (requested) {
     requested.click();
   } else if (tabs.length > 0) {
     tabs[0].click();
   }
   ```
   This is the only change to a shared function; it's purely additive and backward-compatible (verified: no page using `[data-tabs]` currently reads or expects any meaning from a `?tab=` param).

### Why a Jinja partial, not an AJAX fragment

The Dashboard tab (and every other tab on this page) already works by rendering its full HTML shell server-side at page load and lazy-fetching only its *data* client-side. Introducing a different mechanism (fetch-and-inject an HTML fragment) for just this one tab would mean two different tab-loading paradigms living side by side on the same page for no benefit — the partial-include approach reuses the exact pattern already proven on this page and requires no new client-side fragment-loading code.

---

## Testing

Same no-frontend-framework verification pattern used in the prior Beasiswa Dashboard work on this page:

- App-boot sanity check.
- Force-render `/beasiswa/` via Flask test client with a real login (test DB), under **two company scenarios**:
  - ETF company session: assert the Sahabat ETF tab panel contains real dashboard markup (e.g. its filter-bar/chart-card structure), not the wrong-company notice.
  - Non-ETF (SMT) company session: assert the panel contains the "Ganti Company" notice text, not dashboard markup — proves the guard survived the move.
- Force-render `/beasiswa/sahabat` (no trailing path) and assert the response is a 302 redirect (Flask's `redirect()` default) whose `Location` header points at `/beasiswa/?tab=sahabat` — not the old full-page 200 response.
- Grep-checks: the new tab button and `{% include %}` line are present in `beasiswa/index.html`; `modules/sahabat_etf/routes.py`'s `/api/*` and `/export/*` route decorators/bodies are unchanged (diff against pre-change content, not just presence); `initSahabatEtf()`'s new guard exists in `sahabat_etf.js`.
- Id-collision check: extract every `id="..."` from the Sahabat ETF partial and confirm none appears anywhere else in the rendered `/beasiswa/` page (all 7 tabs combined) — see "Known risk: DOM id collisions" above.
- Full Python regression suite run once at the end — no data-layer changes in this task, only routing/rendering, so no new failures expected beyond whatever pre-existing/unrelated failures are already known from prior sessions.
- Manual browser check (if a preview session with non-production data is available): click through all 7 tabs from `/beasiswa/`, confirm no page reload and the tab bar stays visible throughout; visit `/beasiswa/sahabat` directly and confirm it lands on the Sahabat ETF tab already selected and populated. Skip if only the shared live production DB is reachable (per established caution from prior sessions about not mutating/screenshotting it).

## Out of Scope

- Any change to `modules/sahabat_etf/service.py` or the underlying SQL/data logic — this is a routing/template restructuring only.
- Any change to the export CSV/XLSX/PDF generation logic.
- Removing the standalone `sahabat_etf/index.html` template entirely — it stays as a thin wrapper around the shared partial in case anything internal still renders it directly (e.g. a stale bookmark to a sub-path that isn't the bare `/beasiswa/sahabat` root, which this plan doesn't audit).
- Applying the same "become a real tab" treatment to any other page's external-link-styled-as-tab pattern, if one exists elsewhere in the app — not requested, out of scope.
