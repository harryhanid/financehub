# FLOW Unified Header Navigation — Design

## Problem

Every page in FLOW currently renders **two stacked navigation rows**:

1. **Global navbar** (`base.html`) — FLOW wordmark, company name, a flat list of every
   top-level module (Dashboard, Beasiswa, Payment Approval Memo, Payment Application,
   Budget, Bank, Sponsorship, Users), the "Cari modul (Alt+K)" search button, user badge,
   dark-mode toggle, logout.
2. **Page-level sub-nav** (rendered per-module) — the current module's name/title, that
   module's own sub-tabs (e.g. Beasiswa: Dashboard, Data Siswa, Data Budget, Data Payment,
   Report Siswa, Rekam Medis, Sahabat ETF), and any page-level action buttons (Filter,
   Full Screen).

Once a user is inside a module, row 1's flat module list is redundant — the user already
knows which module they're in and rarely needs to see all seven other modules listed at
once. The two rows together also eat a fixed ~90px of vertical space on every single page,
shrinking the actual content area.

## Goal

Collapse both rows into **one single header row** that is context-sensitive:

- On the top-level **Dashboard** (home): shows the flat module list, same as today.
- **Inside any module**: shows that module's own name as a dropdown trigger
  (`[Module Name] ▾`) followed by that module's own sub-tabs, instead of the flat
  cross-module list.
- Switching to a different top-level module happens via clicking the dropdown, or via
  the existing Alt+K command palette (unchanged, just triggered by a small icon instead
  of a labeled button).

This becomes the **standard header pattern for every module going forward**, not a
one-off for Beasiswa.

## Current State — Navigation Patterns Are Inconsistent

Before this change, modules already implement their own sub-navigation several
different ways:

| Pattern | Modules | Mechanism |
|---|---|---|
| Single-page JS tab panels | Beasiswa (7 tabs), Payment Memo (9 tabs) | Click a `<button data-tab>`, JS shows/hides a `.tab-panel`, no page reload. Existing Alt+←/→ shortcuts navigate between tabs. |
| Query-param tabs, full reload | **Payment Application** (nav label — actually backed by the `etf_payment_application` blueprint, `/etf-payment-application`) | Each tab is a link to the same route with a different `?tab=` value; the server re-renders the page with that tab's content. Same visual pill-tab treatment as the JS-panel pattern. |
| Separate pages, plain link tabs | Sponsorship (4 tabs) | Each tab is a real `<a href>` to its own route/template, styled as a pill via `_toolbar.html`. |
| Separate pages, mixed toolbar | Budget (3 "tabs" + 5 filter selects) | Navigation links (Kelola Budget / Realisasi / Carryover) and page filters live in the same `.budget-toolbar` div, undifferentiated. |
| No sub-nav | Bank, Users, Dashboard | Single flat page, just an `<h1>`. |

Note: there is a second, separate `payment_application` blueprint (`/payment-application`)
that is **not linked from anywhere in the app** and does not appear in `DASHBOARD_TABS` —
it looks like unwired/dead code. It is out of scope here; nothing in this redesign
touches it.

This redesign does not unify *how* each module's tabs work internally — it only
standardizes **where** that sub-navigation is displayed (in the header, styled
consistently) and **normalizes Budget's mixed toolbar** so its real navigation links are
distinguishable from its filters.

## Design

### Header states

**State A — Dashboard (home), no module entered:**

```
FLOW  |  Dashboard  Beasiswa  Payment Approval Memo  Payment Application  Budget  Bank  Sponsorship  Users   ⋯scroll⋯   [🔍] [Eka Tjipta Foundation] [admin] [☀] [Keluar]
```

Identical in spirit to today's row 1 module list — just now it's the *only* row, and the
company name has moved from the left (next to FLOW) to the right (replacing where the
"Cari modul" search button used to sit).

**State B — inside a module with its own sub-tabs (e.g. Beasiswa):**

```
FLOW  |  Beasiswa ▾  |  Dashboard  Data Siswa  Data Budget  Data Payment  Report Siswa  Rekam Medis  Sahabat ETF   ⋯scroll⋯   [🔍] [Eka Tjipta Foundation] [admin] [☀] [Keluar]
```

`Beasiswa ▾` is a dropdown trigger. Clicking it opens a small menu listing every
top-level module (same list/order as State A), letting the user jump directly to
another module without returning to Dashboard first.

**State C — inside a module with no sub-tabs of its own (Bank, Users):**

```
FLOW  |  Bank ▾   ⋯empty⋯   [🔍] [Eka Tjipta Foundation] [admin] [☀] [Keluar]
```

Same dropdown trigger as State B, simply nothing rendered beside it. This is the
fallback default — a module that hasn't wired up its own tab list (whether by design,
like Bank, or because it's newly built and not yet migrated) never breaks the header;
it just shows the bare dropdown.

### Module-switch dropdown

- Content: the same module list already powering today's flat nav and the Alt+K
  palette (`DASHBOARD_TABS` → `nav_modules` context processor in `app.py`) — no new data
  source.
- The currently-active module is visually marked (e.g. accent-colored) inside the
  dropdown, matching the existing "active" treatment.
- This is a lightweight, non-searchable list — it exists for quick, one-click switching
  between the small number of modules. It is not a replacement for Alt+K.

### Alt+K / command palette

- Unchanged behavior — same modal, same "recently visited" + "all modules" sections,
  same Coming Soon badges.
- Visual change only: the labeled `Cari modul Alt+K` button is replaced by a small
  icon-only button (magnifying glass), positioned just left of the company name on the
  right side of the header. Hover/title text still reads "Cari modul (Alt+K)" for
  discoverability.

### Filter / Full Screen / page-level toolbars

Every "Filter", "Full Screen", and (for Budget) filter-select controls currently living
in the page-level sub-nav row move **out of the header** into a slim toolbar row that is
part of the page content area, directly below the header, right above the module's main
content. This keeps the header itself lean (navigation only) while preserving every
existing filter/action control.

For Budget specifically, its `.budget-toolbar` div gets split:
- The 3 real navigation links (Kelola Budget, Kelola Realisasi, Carryover / Tambahan)
  move up into the header as this module's sub-tabs (State B pattern).
- The 5 filter `<select>` elements + "Terapkan Filter" button move down into the
  page-content toolbar row, same slot as Beasiswa's "Filter" button today.

### Scroll & overflow

The sub-tab list (and the flat Dashboard module list) scrolls horizontally when it
doesn't fit — this already exists today on `.navbar-menu` (`overflow-x: auto;
scrollbar-width: none`) and is simply reused/extended to the new per-module tab list.
A subtle fade gradient is added on the trailing edge whenever the list actually
overflows, so it's visually obvious there's more to scroll (the scrollbar itself stays
hidden, matching current style). No tabs are ever hidden behind a "More" menu — this
matters most for Payment Memo, which has 9 tabs.

### What does not change

- Each module's internal tab-switching mechanism (JS panel vs real page link) is
  untouched — only the markup's position and styling move.
- The Alt+K palette's data, search, and keyboard shortcut are untouched.
- Existing Alt+←/→ tab-navigation shortcuts are untouched.
- `wrong_company` notices, company-gating guards, and all other business logic are
  untouched — this is a presentation-layer change only.

## Technical Approach

- Introduce one shared header partial in `base.html` (or an included macro) that renders
  the FLOW wordmark, then branches:
  - if no `active_page` / not inside a module → render the flat `nav_modules` list
    (State A)
  - else → render `{{ module_label }} ▾` (the dropdown trigger + its popup menu, sourced
    from `nav_modules`) followed by an optional `module_tabs` list (State B/C) — each
    module's route already knows which case it is and passes `module_tabs` accordingly
    (empty list for Bank/Users).
- Each module keeps producing its own tab items exactly as it does today (`<a href>` for
  Sponsorship/Budget-style pages, `<button data-tab>` for JS-panel modules) — the shared
  partial only needs one CSS class set (`.fh-menu` / `.fh-item`) applied consistently so
  they look identical regardless of the underlying mechanism.
- Company name, search icon, user badge, toggle, and logout move to a `navbar-right`
  block, unconditionally rendered after whichever module-nav content precedes it.

## Migration Order

1. Build the shared header component (dropdown, scroll+fade tab strip, relocated
   search icon/company name) in `base.html`, wired to render State A on Dashboard.
2. Migrate modules that already have clean, ready-to-move tab bars: Beasiswa, Payment
   Memo, Payment Application (`etf_payment_application`). Hoist their existing
   Filter/Full Screen controls into the new page-content toolbar row.
3. Migrate modules with no sub-nav today: Bank, Users (bare dropdown, State C).
4. Migrate modules needing restructuring first: Sponsorship (move its existing
   `_toolbar.html` tab links into the header), Budget (split nav links from filters as
   described above).
5. Full regression pass across every module — this template is shared by the entire
   app, so every module needs a manual smoke-test pass after the change, not just the
   ones with new automated test coverage.

## Testing

- No business logic changes, so existing route-level tests (guards, tab content
  assertions, `wrong_company` checks) should keep passing unchanged. Any test asserting
  a specific structural detail of the old two-row header will need its assertion
  updated to match the new markup.
- New behavior needing coverage: module-switch dropdown lists the correct modules and
  navigates correctly; correct module/tab is highlighted as active in every state (A/B/C).
  This is primarily manual browser smoke-testing, per this project's existing precedent
  for UI-layer changes.
- Because `base.html` is shared by literally every page, the final regression pass must
  visually check every module individually, not rely solely on automated test coverage.

## Out of Scope

- Redesigning how any individual module's tabs *work* internally (JS panels vs page
  links) — only their position/styling in the header changes.
- Mobile/narrow-viewport-specific layout beyond the existing horizontal-scroll behavior
  already used by `.navbar-menu` today.
- Any change to the Alt+K palette's search/filtering logic, or to `nav_modules`'/
  `DASHBOARD_TABS`' data source.
