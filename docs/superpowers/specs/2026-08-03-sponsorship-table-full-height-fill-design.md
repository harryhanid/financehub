# Sponsorship Data/Outstanding — Full-Height Table Fill — Design

## Problem

Sponsorship's Data and Outstanding tabs are already marked full-bleed
(`{% set full_bleed = true %}`, per the 2026-07-31 full-bleed-table-pages
design), but their table wrapper — `.budget-table-container`
(`app/static/css/budget.css:109-114`) — still caps its height with a stale
hardcoded rule:

```css
.budget-table-container {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  ...
}
```

`220px` was calibrated for the old layout, before full-bleed removed
`.main`'s padding and the sticky header's padding-bottom. On a full-bleed
page there's now more usable vertical space than `220px` accounts for, so
the table container stops short of the viewport bottom — leaving a visible
empty gap between the last row and the floating pagination bar (Data tab)
or the bottom of the viewport (Outstanding tab, which has no pagination at
all).

Payment Application's AGRI (and the other pillar) tabs don't have this
problem because they never use a hardcoded height guess in the first place:
`#pa-scroll-wrap` (`app/templates/etf_payment_application/index.html:385,
1088-1105`) sizes itself via JS on every load/resize —
`wrap.style.height = (window.innerHeight - wrap.getBoundingClientRect().top - mainPadBottom) + 'px'`
— with a `ResizeObserver` on the page header so it recomputes if that
header's height changes (e.g. a bulk-action bar appearing). This tracks the
*actual* rendered layout instead of guessing a magic number, so it can't go
stale when the layout around it changes.

## Goal

Make Sponsorship's Data and Outstanding table wrappers fill the remaining
viewport exactly the same way PA's AGRI tab does — same technique, ported
as directly as possible — without touching PA itself, without touching
`.budget-table-container`'s shared CSS rule (other modules using that class
are out of scope here), and without changing the Data tab's existing
floating-pagination behavior.

## Design

### Give each wrapper its own id

`data.html:60` and `outstanding.html:79` both currently have
`<div class="budget-table-container">` with no `id`. Both get
`id="sp-table-wrap"` added (kept alongside the existing class, which still
supplies border/background/shadow styling — only its `max-height` is
overridden). Using a page-specific id — the same pattern PA already uses
with `#pa-scroll-wrap` — means the override only applies here, never
touching `.budget-table-container` consumers in any other module (Budget,
Beasiswa, Bank).

### CSS override

Added once to `app/static/css/sponsorship.css` — already linked by both
`data.html:7` and `outstanding.html:7`, so no new stylesheet link is
needed (unlike `dashboard.html`, which additionally links
`sponsorship_dashboard.css` for its scorecards — Data/Outstanding don't use
that file and don't need to start):

```css
#sp-table-wrap { max-height: none; }
```

An id selector already outranks `.budget-table-container`'s class selector
in specificity, so no `!important` is needed. `overflow-y: auto` and the
rest of `.budget-table-container`'s styling (border, background, shadow)
stay in effect — only the height cap is replaced, by JS, below.

### JS: port `sizeWrap()` from PA, one copy per template

Each of `data.html` and `outstanding.html` gets its own inline copy of the
sizing script (matching PA's own inline-per-template placement — this
isn't extracted into a shared file, since PA's copy isn't either, and the
element ids/observed nodes differ per page):

```js
(function() {
  function sizeWrap() {
    const wrap = document.getElementById('sp-table-wrap');
    if (!wrap) return;
    requestAnimationFrame(() => {
      wrap.style.height = (window.innerHeight - wrap.getBoundingClientRect().top) + 'px';
    });
  }
  window.addEventListener('load', sizeWrap);
  window.addEventListener('resize', sizeWrap);
  document.addEventListener('DOMContentLoaded', sizeWrap);
  document.addEventListener('DOMContentLoaded', () => {
    const filterForm = document.getElementById('sp-data-filter-form');
    if (filterForm && window.ResizeObserver) new ResizeObserver(sizeWrap).observe(filterForm);
  });
})();
```

(No `mainPadBottom` subtraction is needed — full-bleed already sets
`.main`'s padding to `0`, matching PA's own comment that its
`mainPadBottom` constant is `0` for the same reason. The `ResizeObserver`
targets `#sp-data-filter-form` — the collapsible filter bar present on both
pages — so opening/closing it recomputes the available height exactly like
PA's bulk-action-bar case.)

### Data tab's existing floating pagination — unchanged

`data.html`'s `.floating-pagination` block and its `initServerPagedDynamicSize`
call (already wired, per the 2026-07-31 dynamic-pagination-page-size
design) are untouched. The pagination bar is `position: fixed`, so it
already floats independently of the table wrapper's height — once the
wrapper correctly fills to the viewport bottom, the bar simply floats over
the now-fully-extended table, exactly as it does on PA's AGRI tab today.

### Outstanding tab — no pagination, fix is JS + CSS only

Outstanding has no pagination controls (renders all matching rows in one
unpaginated table, per the 2026-07-31 dynamic-pagination spec's own
"out of scope" note for this tab). It only needs the id + CSS override + JS
sizing script — nothing else changes.

## Testing

No existing automated test asserts anything about container height or
JS-driven sizing (same precedent as the original full-bleed and
dynamic-pagination specs — pure presentation-layer behavior). Verification
is manual: open Data with enough rows to require scrolling, confirm the
table wrapper's bottom edge reaches the viewport bottom with no gap before
the floating pagination bar; open Outstanding, confirm the same with no gap
before the viewport bottom; toggle the filter bar open/closed on both pages
and confirm the wrapper resizes to still exactly fill the remaining space;
resize the browser window and confirm it recomputes (matching PA's existing
resize-triggered behavior).

## Out of Scope

- `.budget-table-container`'s shared CSS rule and any other module using
  it (Budget, Beasiswa, Bank) — those may have the same stale-height
  symptom on their own full-bleed tabs, but fixing them is a separate
  effort; this spec only touches Sponsorship's two pages via the new
  page-specific id.
- The Data tab's pagination mechanism itself (page size, floating bar
  styling, dynamic page-size calibration) — already built, unchanged here.
- Payment Application / `#pa-scroll-wrap` — the reference implementation,
  not modified.
