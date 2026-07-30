# FLOW Module-Switcher Carousel (Alt+Down) — Design

## Problem

Today, `Alt+Down` opens a simple searchable list overlay (`#fh-cmd-ov` /
`initCommandPalette()`) to jump between FLOW's modules. It works, but it's
plain text-on-dark-background and doesn't reflect FLOW's established visual
language (the glassmorphism double-bezel cards, ambient glow, and flow-line
motif already shipped on the login and Ganti Perusahaan screens). It also
gives no preview of what's inside a module before you commit to opening it.

Separately, this same overlay has a live bug: its module list is a
hardcoded client-side array (`FH_MODULES` in `app.js`) that does not know
which company is active, so an ETF user still sees "Sponsorship" as a
clickable entry (SMT-only) and an SMT user still sees "Beasiswa"
(ETF-only) — both lead to the module's own wrong-company notice on click.
The navbar's flat list and the header's `{{ module_label }} ▾` dropdown
already filter correctly (`inject_nav_modules()` in `app.py`, commit
`1b72a19`); this overlay was never updated to match.

## Goal

Replace the list-based Alt+Down overlay with an animated card carousel
that matches FLOW's brand language, previews each module's sub-tabs, lets
sub-tabs be opened directly, and is built on the same company-gated data
source as the rest of the navigation (fixing the stale-module bug as a
byproduct, not a separate task).

## Scope

- Rebuilds the *contents and interaction* of the existing `#fh-cmd-ov`
  overlay (trigger, backdrop, Esc-close, click-outside-close, Alt+Down
  toggle all already exist and are reused as-is).
- Adds one new small server-side data structure: each module's sub-tab
  preview list, merged into `nav_modules`.
- **Does not** touch the header's `{{ module_label }} ▾` dropdown
  (`.fh-mod-dd`) — that stays exactly as shipped in the unified-header-nav
  plan. This carousel is a richer alternative for Alt+Down specifically,
  not a replacement for the one-click header dropdown.
- **Does not** touch Alt+Up (Ganti Perusahaan), Alt+Left/Right (in-module
  tab stepping), F/Esc (filter panel), or any route/business logic.
- **Does not** touch the "Coming Soon" placeholder entries (Account
  Payable, Advance, Petty Cash) — they keep appearing, disabled, exactly
  as today.

## Design

### Visual direction (approved via visual companion)

Double-bezel card carousel on a dark, blurred backdrop over the current
page (not a full-screen takeover — Alt+Down is used many times a day, so
it must stay lightweight and never fully hide the page underneath):

- **Backdrop:** `rgba(6,8,15,.68)` + `backdrop-filter: blur(4px)` over the
  current page, same weight as today's `#fh-cmd-ov` backdrop.
- **Search box:** unchanged position/behavior (top, auto-focused, typing
  filters). Filtering re-centers the carousel on the first match instead
  of re-rendering a list.
- **Center card:** double-bezel (`rgba(255,255,255,.03)` outer shell +
  `#0F1220` inner panel, matching the login/company-select signature
  card treatment), with a soft pulsing radial glow behind it
  (`rgba(91,140,255,.28)`, 3.2s ease-in-out breathe). Rises in with
  `cubic-bezier(.22,.72,0,1)` on open.
- **Side cards:** the previous/next module in the filtered list, shown
  scaled to `.82`, translated down slightly, `opacity: .38`, flanking the
  center card (overlapping it by ~18px) — signals "there's more to
  browse" without needing a hint label.
- **Per-module icon:** small (40×40) flow-line-style SVG icon (thin
  stroke, no fill, cobalt→cyan gradient fill on its rounded-square
  background) — one new icon per module, listed under Components below.
- **Sub-tab list:** under the module name, each sub-tab renders as its own
  row, staggered fade-in (`~50ms` apart) as the card becomes active. The
  module's currently-active tab (only meaningful when the carousel is
  opened *from inside* that module) gets an accent-colored pulsing dot.
- **Dots indicator:** below the carousel, one dot per module in the
  current (filtered) set; the active one stretches into a small pill
  (matches the existing `.tab-btn.active` gradient-pill treatment).
- **Arrows:** small circular buttons flanking the carousel; on hover they
  fill with the cobalt→cyan gradient and glow, matching `.fh-mod-trigger`
  hover language already shipped.

### Interaction model

- **Open:** `Alt+Down` (unchanged trigger). Opens centered on the
  currently-active module if inside one, otherwise on Dashboard (first
  entry).
- **Browse:** `←`/`→` keys, or mouse-drag / touch-swipe on the card row,
  step to the previous/next card in the current (filtered) set.
- **Search:** typing in the search box filters the module set live; the
  carousel jumps to the first match. Clearing the search restores the
  full set, re-centered on wherever you were.
- **Open a module:** `Enter`, or click the center card itself, navigates
  to that module's default page.
- **Open a specific sub-tab:** click on any sub-tab row inside the center
  card — navigates straight to `<module-url>?tab=<tab-key>`, reusing the
  `?tab=` deep-link support `initTabs()` already implements for every
  module (no new server-side logic needed for this to work).
- **Close:** `Esc`, or click on the backdrop outside the card row.

### Components

**New per-module icon set** (all 40×40, `stroke-width:1.8`, no fill,
rounded-square gradient background matching the existing navbar-brand
icon treatment) for: Dashboard, Beasiswa, Payment Approval Memo, Payment
Application, Budget, Bank, Sponsorship, Users. Exact SVG paths finalized
during implementation to read cleanly at 40px — kept simple, one
recognizable glyph per module (e.g., a graduation-cap-like mark for
Beasiswa, a receipt/document mark for Payment Approval Memo), consistent
with the existing flow-line stroke style rather than filled icon sets.

### Data

**Problem:** sub-tab labels currently exist only as markup inside each
module's own template (the `{% block module_tabs %}` override from the
unified-header-nav work). The carousel needs to show them from any page,
so a small server-side registry is added — additive to `nav_modules`, not
a replacement for it (`nav_modules` remains the single source of truth
for *which modules exist and their URLs*; this only adds *what's inside
each one* for the preview).

In `app/app.py`'s `inject_nav_modules()`, after building the existing
(already company-filtered) `nav_modules` list, attach a `subtabs` list to
each entry from a new `MODULE_SUBTABS` dict (module `key` → list of
`{label, tab}` — `tab` is the `?tab=` value `initTabs()` already reads).
Payment Approval Memo's list depends on `company_code` exactly like its
own header tabs do:

- `dashboard`: `[]`
- `beasiswa`: Dashboard/`dashboard`, Data Siswa/`siswa`, Data Budget/`budget`, Data Payment/`payment`, Report Siswa/`laporan`, Rekam Medis/`rekam`, Sahabat ETF/`sahabat`
- `payment_memo` (SMT): Open PAM/`draft-pay`, Input/`input-payment`, PAM List/`smt`, Advance/`advance`, Print Memo/`draft-memo`
- `payment_memo` (non-SMT): Open PAM/`draft-pay`, Input/`input-payment`, AGRI/`pam`, APP/`fiori`, LAND/`sml`, SETF/`setf`, Advance/`pa-advance`, Vendors/`vendors`, Print Memo/`draft-memo`
- `etf_payment_app`: Open PA/`summary`, Advance/`advance`, Input/`input`, AGRI/`agri`, APP/`app`, LAND/`sml`, SETF/`setf`
- `budget`: Kelola Budget (links to `/budget/master`), Kelola Realisasi (`/budget/realisasi`), Carryover / Tambahan (`/budget/carryover`) — these are separate routes, not `?tab=` on one page, so `subtabs` entries carry a full `url` instead of a `tab` key for this module specifically
- `bank`: Mutasi & Saldo/`mutasi`, Open/`open`
- `sponsorship`: Dashboard (`/sponsorship/`), Input (`/sponsorship/input`), Data (`/sponsorship/data`), Report (`/sponsorship/report`) — separate routes, same `url`-instead-of-`tab` treatment as Budget
- `users`: `[]`

Because this is built from the already-filtered `nav_modules` list, an ETF
session never receives a `sponsorship` entry at all (and vice versa for
Beasiswa/SMT) — fixing the stale `FH_MODULES` bug as a direct consequence
of switching the carousel's data source, not a separate fix.

**Client-side:** `nav_modules` (now carrying `subtabs`) is serialized into
a `<script type="application/json" id="fh-nav-modules-data">` tag in
`base.html` (Jinja `| tojson`) and parsed once by `app.js`. The existing
static `FH_MODULES` array stays for the 3 "Coming Soon" placeholder
entries only (they have no URL/company concept to gate) and is merged
with the server data when building the carousel's card set — real modules
come from the server, disabled placeholders still come from the static
list.

### Technical approach

Reuse `#fh-cmd-ov`'s existing lifecycle (open/close, Alt+Down binding,
Escape, click-outside — all in `initCommandPalette()`) unchanged. Replace
only:
- `render(query)`'s output: build the carousel markup (center + 2 side
  cards + dots) instead of the `.fh-cmd-item` list.
- Keyboard handling inside the overlay: `ArrowLeft`/`ArrowRight` step the
  carousel (replacing today's `ArrowUp`/`ArrowDown` list-selection, which
  doesn't apply to a horizontal carousel); `Enter` opens the centered
  card instead of the highlighted list row.
- Data source: `nav_modules` (parsed from the JSON script tag) + the
  static Coming-Soon subset of `FH_MODULES`, instead of all of
  `FH_MODULES`.

`_fhRecordVisit()` keeps being called on module open (harmless, costs
nothing, may be useful for a future feature) but `_fhGetRecent()`'s output
has no consumer in this design — the new carousel has no separate
"recently visited" section; it opens centered on the module you're
currently in (or Dashboard as the natural entry point) instead of showing
a distinct recent-items list first. Removing the now-unused
`_fhGetRecent()` call site inside `render()` is part of this task (it
built the old list's "TERAKHIR DIKUNJUNGI" section, which no longer
exists); the function itself can stay defined and unused, or be removed —
implementer's call, not a functional requirement either way.

## Testing

- Route-level: extend `test_dashboard.py`'s existing company-gating tests
  (`test_navbar_hides_sponsorship_for_etf`,
  `test_navbar_hides_beasiswa_for_smt`) to also assert the new `subtabs`
  data is absent for the hidden module and correct for the visible ones,
  and that Payment Approval Memo's `subtabs` differ by `company_code`.
- Manual browser smoke test (this is a pure animation/interaction feature,
  consistent with this project's precedent of manual verification for
  UI-layer work): open the carousel from at least 3 different modules,
  browse with arrows and drag/swipe, search-filter and confirm re-centering,
  click a sub-tab and confirm it lands on that exact tab, confirm an ETF
  session never shows a Sponsorship card and an SMT session never shows a
  Beasiswa card, confirm dark/light theme both render correctly, confirm
  `prefers-reduced-motion` disables the glow-pulse/float animations
  (matching the existing pattern already used on `company_select.html`).

## Out of Scope

- Any change to the header's `.fh-mod-dd` click dropdown.
- Any change to Alt+Up, Alt+Left/Right, F/Esc filter shortcuts.
- Any change to the "Coming Soon" module list or its badge treatment.
- Mobile-specific layout beyond the swipe gesture itself (this is an
  internal desktop-first tool, consistent with the rest of FLOW).
