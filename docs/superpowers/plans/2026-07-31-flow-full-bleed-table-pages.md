# FLOW Full-Bleed Table Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `.main`'s fixed padding and the sticky header's residual gap for every table-heavy tab/page across FinanceHub, so those tables fill the viewport edge-to-edge like a spreadsheet — while forms/dashboards/charts keep their current padding — per `docs/superpowers/specs/2026-07-31-flow-full-bleed-table-pages-design.md`.

**Architecture:** A single `fh-full-bleed` class on `<body>` drives two CSS rules (zero `.main` padding, zero `.fh-page-header` bottom padding) plus a full-bleed variant of two hardcoded `calc(100vw - 3.5rem)` table-wrap widths. Two ways to set the class, matching how each module's tabs already work: single-page-per-tab / single-page-only modules set it via a template-level `{% set full_bleed = ... %}` that `base.html`'s `<body>` tag reads (no JS — every full-bleed view is its own page load or, for Bank, a page where every tab qualifies). Beasiswa and Payment Memo — the only two modules mixing full-bleed and non-full-bleed tabs in one client-side-switched page — mark each qualifying `.tab-panel` with `data-full-bleed="true"`, and `initTabs()`'s existing per-click handler (which already runs on every tab switch, including the automatic activation on page load) toggles the body class to match.

**Tech Stack:** Vanilla JS (`app/static/js/app.js`), CSS (`app/static/css/style.css`), Jinja2 templates. No new dependencies, no backend/database changes.

## Global Constraints

- Presentation-layer only — no route, business-logic, or database changes anywhere (spec "What does not change").
- `F`/`Esc` collapsible-filter behavior (open/close, sessionStorage persistence, force-close on tab-switch) is completely untouched by this work (spec "What does not change").
- Non-qualifying tabs/pages (Dashboard views, Input forms, Report Siswa, Print Memo) keep their current padding — do not touch their markup or styling.
- The classification rule is "is the tab's main content a data table?" — not the enumerated list. If a step in this plan and the live template disagree, re-classify by reading the template, the same way two scope corrections were already caught this way during planning (Beasiswa's Rekam Medis was missing; Payment Memo's Print Memo was wrongly included).
- Full-bleed scope, exactly as verified against the live templates:
  - **Full-bleed:** Beasiswa (Data Siswa, Data Budget, Data Payment, Rekam Medis, Sahabat ETF); Payment Memo (Open PAM, PAM List/AGRI/APP/LAND/SETF/Advance/Vendors — i.e. every tab except Input and Print Memo); Payment Application (every tab except Input); Sponsorship (Data, Outstanding, Report); Bank (both tabs — Mutasi & Saldo, Open); Budget (Master, Realisasi, Carryover); Users (its one page).
  - **Not full-bleed:** Beasiswa (Dashboard, Report Siswa); Payment Memo (Input, Print Memo); Payment Application (Input); Sponsorship (Dashboard, Input); Budget (Dashboard).

## File Structure

- `app/static/css/style.css` — new `body.fh-full-bleed .main`, `body.fh-full-bleed .fh-page-header`, and the two hardcoded-width overrides.
- `app/templates/base.html` — `<body>` tag reads a new `full_bleed` template variable.
- `app/static/js/app.js` — `initTabs()`'s click handler toggles `body.fh-full-bleed` based on the newly-active panel's `data-full-bleed` attribute.
- `app/templates/beasiswa/index.html`, `app/templates/payment_memo/index.html` — mark qualifying `.tab-panel` elements with `data-full-bleed="true"`.
- `app/templates/etf_payment_application/index.html` — root-level `{% set full_bleed = active_tab != 'input' %}`.
- `app/templates/bank/index.html`, `app/templates/users/index.html` — root-level `{% set full_bleed = true %}` (every tab/page in these two templates qualifies).
- `app/templates/sponsorship/data.html`, `app/templates/sponsorship/outstanding.html`, `app/templates/sponsorship/report.html` — root-level `{% set full_bleed = true %}`.
- `app/templates/budget/master_list.html`, `app/templates/budget/realisasi_list.html`, `app/templates/budget/carryover.html` — root-level `{% set full_bleed = true %}`.

---

### Task 1: Shared foundation (CSS + base.html + app.js)

**Files:**
- Modify: `app/static/css/style.css` (two insertions, see steps)
- Modify: `app/templates/base.html:17`
- Modify: `app/static/js/app.js:460-461`

**Interfaces:**
- Produces: `body.fh-full-bleed` CSS class contract — every later task sets this via either a Jinja `full_bleed` template variable (read by `base.html`) or a `data-full-bleed="true"` attribute on a `.tab-panel` (read by `initTabs()`). No other task depends on anything else from this one.

- [ ] **Step 1: Confirm current line content matches this plan**

Run: `grep -n "^\.main {" -A 5 app/static/css/style.css && grep -n "\.fh-page-header {" -A 8 app/static/css/style.css && grep -n "^<body" app/templates/base.html && grep -n "target.classList.add" app/static/js/app.js`

Expected (line numbers may have drifted slightly from concurrent commits — if the *content* shown doesn't match, stop and re-locate by content before proceeding, don't guess):

```
503:.main {
504-  margin-top: var(--navbar-h);
505-  padding: 1.625rem 1.75rem;
506-  min-height: calc(100dvh - var(--navbar-h));
507-}
762:.fh-page-header {
763-  position: sticky;
764-  top: var(--navbar-h, 56px);
765-  z-index: 20;
766-  background: var(--bg, #f8fafc);
767-  padding-bottom: .5rem;
768-  margin-bottom: 0;
769-}
17:<body data-module="{{ active_page or '' }}">
460:      const target = container.querySelector(`#${btn.dataset.tab}`);
461:      if (target) target.classList.add("active");
```

- [ ] **Step 2: Add the full-bleed CSS rules**

Insert immediately after the `.main { ... }` block (after line 507, before the `/* ── Page Header ── */` comment):

```css

/* ── Full-bleed table pages ──────────────────────────────────────── */
/* Set on <body> for pages/tabs whose main content is a data table —   */
/* see docs/superpowers/specs/2026-07-31-flow-full-bleed-table-pages-  */
/* design.md. Zeroes .main's padding and the sticky header's residual  */
/* bottom gap so the table fills the viewport like a spreadsheet.      */
body.fh-full-bleed .main { padding: 0; }
body.fh-full-bleed .fh-page-header { padding-bottom: 0; }
/* Two table-wrap widths hardcode calc(100vw - 3.5rem) — 3.5rem being  */
/* .main's old side padding (1.75rem × 2) — as a workaround to escape  */
/* .main's constrained width. With .main's padding now zero on these   */
/* pages, that stale calc leaves an unwanted 56px gap; use the full    */
/* container width instead. */
body.fh-full-bleed #pa-scroll-wrap,
body.fh-full-bleed .pillar-table-wrap { width: 100% !important; }
```

- [ ] **Step 3: Wire the `full_bleed` template variable into `base.html`**

Replace (current line 17):

```html
<body data-module="{{ active_page or '' }}">
```

with:

```html
<body data-module="{{ active_page or '' }}"{% if full_bleed %} class="fh-full-bleed"{% endif %}>
```

- [ ] **Step 4: Toggle the body class on tab switch in `app.js`**

Replace (current lines 460-461, inside `initTabs()`'s click handler):

```javascript
      const target = container.querySelector(`#${btn.dataset.tab}`);
      if (target) target.classList.add("active");
```

with:

```javascript
      const target = container.querySelector(`#${btn.dataset.tab}`);
      if (target) {
        target.classList.add("active");
        // Full-bleed pages (spec: 2026-07-31-flow-full-bleed-table-pages) —
        // toggled per-tab since Beasiswa/Payment Memo mix full-bleed data
        // tabs with non-full-bleed dashboard/form tabs in one page. This
        // same click handler also fires on initTabs()'s own auto-activation
        // at page load, so the correct state is set immediately on load too.
        document.body.classList.toggle("fh-full-bleed", target.dataset.fullBleed === "true");
      }
```

- [ ] **Step 5: Sanity-check JS syntax**

Run: `cd app && node --check static/js/app.js`
Expected: no output, exit code 0.

- [ ] **Step 6: Manual visual check**

Start the dev server, log in, visit `/dashboard` (a page with no `full_bleed` set anywhere) and confirm it looks unchanged — `.main` still has its normal padding. This confirms the new CSS/JS is inert until a later task actually sets the flag somewhere.

- [ ] **Step 7: Commit**

```bash
git add app/static/css/style.css app/templates/base.html app/static/js/app.js
git commit -m "feat: add fh-full-bleed body-class foundation for table pages"
```

---

### Task 2: Migrate Beasiswa

**Files:**
- Modify: `app/templates/beasiswa/index.html:208,278,435,545,604`

**Interfaces:**
- Consumes: `data-full-bleed="true"` attribute contract from Task 1 (read by `initTabs()`'s click handler).

**Note:** re-check `git status --porcelain -- app/templates/beasiswa/index.html` before editing — this file has had recurring concurrent-session WIP throughout this project.

- [ ] **Step 1: Confirm current tab-panel lines**

Run: `grep -n 'class="tab-panel"' app/templates/beasiswa/index.html`
Expected:
```
30:  <div class="tab-panel" id="tab-dashboard">
208:  <div class="tab-panel" id="tab-siswa">
278:  <div class="tab-panel" id="tab-budget">
377:  <div class="tab-panel" id="tab-laporan">
435:  <div class="tab-panel" id="tab-payment">
545:  <div class="tab-panel" id="tab-rekam">
604:  <div class="tab-panel" id="tab-sahabat">
```
If these line numbers or ids have drifted, locate each by its `id` rather than by line number.

- [ ] **Step 2: Mark the 5 qualifying tab-panels**

Replace each of the following (leaving `tab-dashboard` and `tab-laporan` untouched — those are the two non-qualifying tabs):

```html
  <div class="tab-panel" id="tab-siswa">
```
with:
```html
  <div class="tab-panel" id="tab-siswa" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-budget">
```
with:
```html
  <div class="tab-panel" id="tab-budget" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-payment">
```
with:
```html
  <div class="tab-panel" id="tab-payment" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-rekam">
```
with:
```html
  <div class="tab-panel" id="tab-rekam" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-sahabat">
```
with:
```html
  <div class="tab-panel" id="tab-sahabat" data-full-bleed="true">
```

- [ ] **Step 3: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_beasiswa_routes.py -v`
Expected: all tests pass unchanged (this is a pure markup addition — no route or rendered-text assertion should be affected).

- [ ] **Step 4: Manual visual check**

Start the dev server, log in, select ETF, visit `/beasiswa/`. Confirm: Dashboard tab (chart/KPI cards) still has normal padding. Click Data Siswa — confirm the table now extends to the browser edges, header row sticks with no visible gap above the table. Click back to Dashboard — confirm padding returns immediately (no reload). Repeat spot-check on Data Budget, Data Payment, Rekam Medis, Sahabat ETF (all full-bleed) and Report Siswa (not full-bleed, should look unchanged). Confirm pressing `F` still opens the filter panel correctly on a full-bleed tab (e.g. Data Siswa) and `Esc` still closes it.

- [ ] **Step 5: Commit**

```bash
git add app/templates/beasiswa/index.html
git commit -m "feat: full-bleed layout for Beasiswa's data-table tabs"
```

---

### Task 3: Migrate Payment Memo

**Files:**
- Modify: `app/templates/payment_memo/index.html:135,438,552,656,738,843,906,978,1040`

**Interfaces:**
- Consumes: `data-full-bleed="true"` attribute contract from Task 1.

**Note:** re-check `git status --porcelain -- app/templates/payment_memo/index.html` before editing — recurring concurrent-session WIP throughout this project.

- [ ] **Step 1: Confirm current tab-panel lines**

Run: `grep -n 'class="tab-panel"' app/templates/payment_memo/index.html`
Expected:
```
135:  <div class="tab-panel" id="tab-draft-pay">
183:  <div class="tab-panel" id="tab-input-payment">
438:  <div class="tab-panel" id="tab-pam">
552:  <div class="tab-panel" id="tab-fiori">
656:  <div class="tab-panel" id="tab-sml">
738:  <div class="tab-panel" id="tab-smt">
843:  <div class="tab-panel" id="tab-advance">
906:  <div class="tab-panel" id="tab-setf">
978:  <div class="tab-panel" id="tab-pa-advance">
1040:  <div class="tab-panel" id="tab-vendors">
1093:  <div class="tab-panel" id="tab-draft-memo">
```
If these have drifted, locate each by its `id`. `tab-input-payment` (Input) and `tab-draft-memo` (Print Memo — a search + document-preview view, not a data table) are the two non-qualifying tabs; every other tab is a data table.

- [ ] **Step 2: Mark the 9 qualifying tab-panels**

Replace each of the following:

```html
  <div class="tab-panel" id="tab-draft-pay">
```
with:
```html
  <div class="tab-panel" id="tab-draft-pay" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-pam">
```
with:
```html
  <div class="tab-panel" id="tab-pam" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-fiori">
```
with:
```html
  <div class="tab-panel" id="tab-fiori" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-sml">
```
with:
```html
  <div class="tab-panel" id="tab-sml" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-smt">
```
with:
```html
  <div class="tab-panel" id="tab-smt" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-advance">
```
with:
```html
  <div class="tab-panel" id="tab-advance" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-setf">
```
with:
```html
  <div class="tab-panel" id="tab-setf" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-pa-advance">
```
with:
```html
  <div class="tab-panel" id="tab-pa-advance" data-full-bleed="true">
```

```html
  <div class="tab-panel" id="tab-vendors">
```
with:
```html
  <div class="tab-panel" id="tab-vendors" data-full-bleed="true">
```

- [ ] **Step 3: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_payment_memo_ipay.py tests/test_payment_memo_open_pam.py tests/test_payment_memo_sla.py tests/test_payment_memo_vendors.py -v`
Expected: all tests pass unchanged.

- [ ] **Step 4: Manual visual check**

Start the dev server, visit `/payment-memo` for both an SMT company (PAM List, Advance tabs) and an ETF company (AGRI/APP/LAND/SETF/Advance/Vendors tabs). Confirm each qualifying tab is full-bleed, Input and Print Memo are unchanged, switching between a full-bleed tab and Input/Print Memo toggles padding immediately with no reload, and `F`/`Esc` still work on a full-bleed tab (e.g. Open PAM).

- [ ] **Step 5: Commit**

```bash
git add app/templates/payment_memo/index.html
git commit -m "feat: full-bleed layout for Payment Memo's data-table tabs"
```

---

### Task 4: Migrate Payment Application

**Files:**
- Modify: `app/templates/etf_payment_application/index.html:1-3`

**Interfaces:**
- Consumes: `full_bleed` Jinja variable contract from Task 1 (read by `base.html`'s `<body>` tag).

**Note:** re-check `git status --porcelain -- app/templates/etf_payment_application/index.html` before editing — recurring concurrent-session WIP.

Unlike Beasiswa/Payment Memo (one page, many JS-switched tabs), every Payment Application tab is a full server-rendered response to `?tab=<name>` from one route — so a single root-level `{% set %}` computed from the already-passed `active_tab` variable covers every tab with no JS/data-attribute needed, and updates correctly on every page load since there's no client-side switching to account for.

- [ ] **Step 1: Confirm current file header matches this plan**

Run: `sed -n '1,3p' app/templates/etf_payment_application/index.html`
Expected:
```
{% extends "base.html" %}
{% block title %}Payment Application{% endblock %}

```

- [ ] **Step 2: Add the root-level `full_bleed` set**

Replace:

```jinja
{% extends "base.html" %}
{% block title %}Payment Application{% endblock %}
```

with:

```jinja
{% extends "base.html" %}
{% set full_bleed = active_tab != 'input' %}
{% block title %}Payment Application{% endblock %}
```

- [ ] **Step 3: Manual smoke check**

No dedicated render test exists for this module's HTML (same as noted in the 2026-07-29 unified-header-navigation plan). Start the dev server, visit `/etf-payment-application` with `?tab=agri` — confirm the table fills the viewport edge-to-edge (the `#pa-scroll-wrap` width fix from Task 1 applies here). Visit `?tab=input` — confirm normal padding (form view, unchanged). Confirm `F`/`Esc` still work on a data tab.

- [ ] **Step 4: Commit**

```bash
git add app/templates/etf_payment_application/index.html
git commit -m "feat: full-bleed layout for Payment Application's data tabs"
```

---

### Task 5: Migrate Sponsorship

**Files:**
- Modify: `app/templates/sponsorship/data.html:1`
- Modify: `app/templates/sponsorship/outstanding.html:1`
- Modify: `app/templates/sponsorship/report.html:1`

**Interfaces:**
- Consumes: `full_bleed` Jinja variable contract from Task 1.

Dashboard and Input are untouched (no `full_bleed` set anywhere in those two templates — defaults to unset/false).

- [ ] **Step 1: `app/templates/sponsorship/data.html`**

Replace:
```jinja
{% extends "base.html" %}
{% block title %}Sponsorship Data
{% endblock %}
```
with:
```jinja
{% extends "base.html" %}
{% set full_bleed = true %}
{% block title %}Sponsorship Data
{% endblock %}
```

- [ ] **Step 2: `app/templates/sponsorship/outstanding.html`**

Replace:
```jinja
{% extends "base.html" %}
{% block title %}Sponsorship Outstanding
{% endblock %}
```
with:
```jinja
{% extends "base.html" %}
{% set full_bleed = true %}
{% block title %}Sponsorship Outstanding
{% endblock %}
```

- [ ] **Step 3: `app/templates/sponsorship/report.html`**

Replace:
```jinja
{% extends "base.html" %}
{% block title %}Sponsorship Report{% endblock %}
```
with:
```jinja
{% extends "base.html" %}
{% set full_bleed = true %}
{% block title %}Sponsorship Report{% endblock %}
```

- [ ] **Step 4: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_sponsorship_routes.py -v`
Expected: all tests pass unchanged, except the two failures already confirmed pre-existing and unrelated to any of this session's sponsorship work (`test_export_report_filename_matches_cat4_and_tahun`, `test_report_page_tahun_dropdown_has_options_for_seeded_years`).

- [ ] **Step 5: Manual visual check**

Visit `/sponsorship/data`, `/sponsorship/outstanding`, `/sponsorship/report` as SMT — confirm all three are full-bleed, `F`/`Esc` still work. Visit `/sponsorship/` (Dashboard) and `/sponsorship/input` — confirm both unchanged.

- [ ] **Step 6: Commit**

```bash
git add app/templates/sponsorship/data.html app/templates/sponsorship/outstanding.html app/templates/sponsorship/report.html
git commit -m "feat: full-bleed layout for Sponsorship's Data/Outstanding/Report"
```

---

### Task 6: Migrate Bank

**Files:**
- Modify: `app/templates/bank/index.html:1`

**Interfaces:**
- Consumes: `full_bleed` Jinja variable contract from Task 1.

Both of Bank's tabs (Mutasi & Saldo, Open) are data tables — no non-qualifying tab exists here, so a single unconditional `{% set full_bleed = true %}` covers the whole page. This is simpler than the data-attribute/JS mechanism Beasiswa/Payment Memo need, since there's no tab to switch *away* to that should turn full-bleed off.

- [ ] **Step 1: Confirm current file header matches this plan**

Run: `sed -n '1,3p' app/templates/bank/index.html`
Expected:
```
{% extends "base.html" %}
{% block title %}Bank{% endblock %}

```

- [ ] **Step 2: Add the root-level `full_bleed` set**

Replace:
```jinja
{% extends "base.html" %}
{% block title %}Bank{% endblock %}
```
with:
```jinja
{% extends "base.html" %}
{% set full_bleed = true %}
{% block title %}Bank{% endblock %}
```

- [ ] **Step 3: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_bank_routes.py -v`
Expected: all tests pass unchanged.

- [ ] **Step 4: Manual visual check**

Visit `/bank` — confirm both Mutasi & Saldo and Open tabs are full-bleed, switching between them keeps the layout full-bleed (no flicker back to padded), and `F`/`Esc` still work.

- [ ] **Step 5: Commit**

```bash
git add app/templates/bank/index.html
git commit -m "feat: full-bleed layout for Bank"
```

---

### Task 7: Migrate Budget

**Files:**
- Modify: `app/templates/budget/master_list.html:1`
- Modify: `app/templates/budget/realisasi_list.html:1`
- Modify: `app/templates/budget/carryover.html:1`

**Interfaces:**
- Consumes: `full_bleed` Jinja variable contract from Task 1.

Budget Dashboard (`budget/dashboard.html`) is untouched — charts, not a table.

- [ ] **Step 1: `app/templates/budget/master_list.html`**

Replace:
```jinja
{% extends "base.html" %}
{% block title %}Budget Master{% endblock %}
```
with:
```jinja
{% extends "base.html" %}
{% set full_bleed = true %}
{% block title %}Budget Master{% endblock %}
```

- [ ] **Step 2: `app/templates/budget/realisasi_list.html`**

Replace:
```jinja
{% extends "base.html" %}
{% block title %}Realisasi{% endblock %}
```
with:
```jinja
{% extends "base.html" %}
{% set full_bleed = true %}
{% block title %}Realisasi{% endblock %}
```

- [ ] **Step 3: `app/templates/budget/carryover.html`**

Replace:
```jinja
{% extends "base.html" %}
{% block title %}Carryover & Additional Budget{% endblock %}
```
with:
```jinja
{% extends "base.html" %}
{% set full_bleed = true %}
{% block title %}Carryover & Additional Budget{% endblock %}
```

- [ ] **Step 4: Manual smoke check**

No dedicated Budget route test file was found in this session's prior work on this repo — check `ls app/tests/ | grep budget` and run whatever exists (e.g. `test_budget_routes.py`/`test_budget_service.py`) if present:

Run: `cd app && python -m pytest tests/test_budget_routes.py tests/test_budget_service.py -v` (skip any filename that doesn't exist)
Expected: all tests pass unchanged, except the already-documented pre-existing `test_nav_stays_visible_on_budget_pages` failure (stale assertion from an unrelated earlier tab-bar refactor, confirmed pre-existing multiple times this session).

Then visit `/budget/master`, `/budget/realisasi`, `/budget/carryover` — confirm all three full-bleed. Visit `/budget/` (Dashboard) — confirm unchanged.

- [ ] **Step 5: Commit**

```bash
git add app/templates/budget/master_list.html app/templates/budget/realisasi_list.html app/templates/budget/carryover.html
git commit -m "feat: full-bleed layout for Budget Master/Realisasi/Carryover"
```

---

### Task 8: Migrate Users

**Files:**
- Modify: `app/templates/users/index.html:1`

**Interfaces:**
- Consumes: `full_bleed` Jinja variable contract from Task 1.

- [ ] **Step 1: Confirm current file header matches this plan**

Run: `sed -n '1,3p' app/templates/users/index.html`
Expected:
```
{% extends "base.html" %}
{% block title %}User Management{% endblock %}

```

- [ ] **Step 2: Add the root-level `full_bleed` set**

Replace:
```jinja
{% extends "base.html" %}
{% block title %}User Management{% endblock %}
```
with:
```jinja
{% extends "base.html" %}
{% set full_bleed = true %}
{% block title %}User Management{% endblock %}
```

- [ ] **Step 3: Run the existing regression suite**

Run: `cd app && python -m pytest tests/test_users_routes.py -v` (if this file doesn't exist, skip this step and note it in the commit)
Expected: all tests pass unchanged.

- [ ] **Step 4: Manual visual check**

Visit `/users` — confirm the table is full-bleed.

- [ ] **Step 5: Commit**

```bash
git add app/templates/users/index.html
git commit -m "feat: full-bleed layout for Users"
```

---

### Task 9: Final regression pass across every module

**Files:** none created — verification only.

- [ ] **Step 1: Run every module's test suite individually**

Per this project's documented Windows SQLite file-lock flakiness, run module test files individually rather than the whole `tests/` directory at once:

```bash
cd app
python -m pytest tests/test_beasiswa_routes.py -v
python -m pytest tests/test_payment_memo_ipay.py tests/test_payment_memo_open_pam.py tests/test_payment_memo_sla.py tests/test_payment_memo_vendors.py -v
python -m pytest tests/test_bank_routes.py -v
python -m pytest tests/test_sponsorship_routes.py -v
python -m pytest tests/test_budget_routes.py tests/test_budget_service.py -v
python -m pytest tests/test_users_routes.py -v
python -m pytest tests/test_dashboard.py -v
```

Expected: all pass except the two already-documented pre-existing failures (`test_export_report_filename_matches_cat4_and_tahun`, `test_report_page_tahun_dropdown_has_options_for_seeded_years` in Sponsorship) and the already-documented pre-existing `test_nav_stays_visible_on_budget_pages` failure in Budget. No new failures anywhere.

- [ ] **Step 2: Full manual sweep**

Using the running dev server, visit every full-bleed tab/page listed in this plan's Global Constraints scope table and confirm: table extends edge-to-edge with no gap on any side, header-to-table vertical gap is minimal, `F` opens and `Esc` closes the filter correctly wherever one exists, and every non-full-bleed tab/page in the same modules (Beasiswa Dashboard/Report Siswa, Payment Memo Input/Print Memo, Payment Application Input, Sponsorship Dashboard/Input, Budget Dashboard) is visually unchanged.

- [ ] **Step 3: Commit any fixes found**

If Step 2 surfaces issues, fix them, re-run the relevant task's tests, and commit as `fix(full-bleed): <description>` — do not batch multiple unrelated fixes into one commit.
