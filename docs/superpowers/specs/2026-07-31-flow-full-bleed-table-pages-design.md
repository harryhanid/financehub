# FLOW Full-Bleed Table Pages — Design

## Problem

Every page shares `.main`'s fixed padding (`1.625rem` top/bottom, `1.75rem`
sides — see `app/static/css/style.css:503-507`) and, where present, the
sticky `.fh-page-header` wrapper's own `padding-bottom: .5rem`
(`style.css:762-769`). For pages whose entire purpose is a large data table
(Payment Application's AGRI/APP/LAND/SETF tabs, Beasiswa's Data Siswa/Data
Budget/Data Payment tabs, Payment Memo's data tabs, Sponsorship's
Data/Outstanding/Report, Bank, Users, Budget's Master/Realisasi/Carryover),
this reserved space is pure waste — less of the table fits on screen, and the
visible gap between the header and the first row reads as unfinished, not
intentional. The user wants these pages to feel like opening a spreadsheet:
the table fills the available viewport edge-to-edge, both horizontally and
vertically.

## Goal

For table-heavy pages/tabs specifically (not every page — forms, dashboards,
and chart views keep their current padding), remove `.main`'s padding
entirely and tighten the gap between the sticky header and the table's first
row, while leaving the `F`/`Esc` collapsible-filter behavior (already
generic, already working across every module that has it) completely
unchanged.

## Scope — which tabs/pages qualify

**Full-bleed:**
- Beasiswa: Data Siswa, Data Budget, Data Payment, Rekam Medis, Sahabat ETF
- Payment Memo: Open PAM, PAM List/AGRI/APP/LAND/SETF/Advance/Vendors
- Payment Application: Open PA/Summary, Advance, AGRI, APP, LAND, SETF
- Sponsorship: Data, Outstanding, Report
- Bank: Mutasi & Saldo, Open
- Budget: Master, Realisasi, Carryover
- Users (single page)

**Not full-bleed (unchanged):**
- Beasiswa: Dashboard (charts/KPI cards), Report Siswa (search + student detail card, not a data table)
- Payment Memo: Input, Print Memo (search + document preview, not a data table)
- Payment Application: Input
- Sponsorship: Dashboard, Input
- Budget: Dashboard (charts)

The rule driving this list: a tab is full-bleed if its main content is a
data table; it isn't if the main content is a form, a dashboard of charts,
or KPI cards. This rule, not the enumerated list itself, is the source of
truth — a future tab should be classified by applying it, not by searching
this list for a literal match.

## Design

### Two activation mechanisms, matched to how each module's tabs work

FinanceHub's modules already split into two families (documented in the
2026-07-29 unified-header-navigation spec): single-page-per-tab modules
(each tab is a full server-rendered page — Payment Application,
Sponsorship) and single-page-many-tabs modules (all tabs live in one page,
switched by client-side JS — Beasiswa, Payment Memo, Bank). Full-bleed
activation follows the same split:

**Single-page-per-tab modules:** the route passes `full_bleed=True` to
`render_template()` for qualifying tabs only. `base.html` adds a
`fh-full-bleed` class to `<body>` when this flag is set. No JS involved —
every full-bleed tab is its own page load, so a plain server-side flag is
sufficient.

**Single-page-many-tabs modules:** each qualifying `<div class="tab-panel">`
gains a `data-full-bleed="true"` attribute. `initTabs()` — which already
runs on every tab click, including the automatic activation on page
load/reload — adds one check: after activating the target panel, toggle
`document.body.classList.toggle('fh-full-bleed', target?.dataset.fullBleed
=== 'true')`. Switching from a table tab to Dashboard removes the class
immediately (and vice versa) with no page reload, matching the "only while
a table tab is active" requirement.

### CSS

```css
body.fh-full-bleed .main { padding: 0; }
body.fh-full-bleed .fh-page-header { padding-bottom: 0; }
```

Both rules key off the `<body>` class so they apply uniformly regardless of
which activation mechanism set it.

### Two hardcoded width calculations need a full-bleed variant

`app/templates/etf_payment_application/index.html:370` and
`app/templates/payment_memo/index.html:19` both hardcode
`width: calc(100vw - 3.5rem)` on their table's scroll wrapper — `3.5rem`
is exactly `.main`'s old side padding (`1.75rem` × 2), a workaround for the
table needing to escape `.main`'s constrained width. Once `.main` has zero
padding on full-bleed pages, this calculation leaves a stale 56px gap on the
right edge — the opposite of the intended effect. Add a
`body.fh-full-bleed` override setting these wraps to `width: 100%` instead
(simpler than editing the inline style, and automatically scoped to exactly
the pages where it matters).

### What does not change

- The `F`/`Esc` collapsible-filter mechanism (open/close, sessionStorage
  persistence across reload, force-close on tab-switch) — completely
  untouched. Opening a filter on a full-bleed page still pushes the table
  down by the filter bar's height, exactly like today; it does not become
  an overlay.
- Non-qualifying tabs/pages (Dashboard views, Input forms) keep their
  current padding unchanged.
- No route, business-logic, or database changes anywhere in this work —
  presentation-layer only, same as every filter/header change so far.

## Testing

No existing automated test asserts anything about `.main`'s padding or
per-tab full-bleed state (this is pure CSS/DOM presentation). Verification
is manual browser smoke-testing per qualifying tab: confirm the table
extends to the browser edges with no visible gap, confirm a non-qualifying
tab in the same module (e.g. Beasiswa's Dashboard) keeps normal padding,
confirm switching between a full-bleed tab and a non-full-bleed tab in the
same page toggles correctly with no flash/reload, and confirm `F`/`Esc`
still open/close the filter and still persist across reload exactly as
before.

## Out of Scope

- Any change to table row height, column width, or other density settings
  beyond the outer page padding — this is about reclaiming the page's own
  margin, not redesigning the tables themselves.
- Any change to the filter panel's open/close mechanism, its persistence,
  or its visual treatment (overlay vs. push-down) — explicitly unchanged.
- Non-qualifying pages (dashboards, forms) — their padding is untouched.
