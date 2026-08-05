# Sponsorship Filter Style Consistency & Year Dropdown Z-Index Fix — Design

## Problem

Sponsorship's Data, Outstanding, and Report tabs share a "Tahun" (year)
filter built as a custom multi-select widget —
`.budget-dropdown-check`/`.budget-dropdown-btn`/`.budget-dropdown-content`
(`budget.css:426-474`) — a button that toggles a checkbox-list popover.
Two problems, both traced to this same widget:

1. **Visual inconsistency.** `.budget-dropdown-btn`'s styling
   (`budget.css:432-444`) uses a different token set
   (`--bg-card`/`--border-color`/`--text-primary`, `border-radius: 8px`,
   `padding: 0.4rem 0.7rem`, `font-size: 0.85rem`) than every plain
   `<select>`/`<input>` in the app — including Sponsorship's own sibling
   filters (Cat/Pillar/Description) and every filter in Payment
   Application (`etf_payment_application/index.html`'s `#pa-filter-panel`)
   — which all inherit the single global rule at `style.css:756-765`
   (`border: var(--sl-300)`, `border-radius: var(--r-md)`,
   `font-size: .8125rem`, `padding: .375rem .6875rem`, `background: #FFF`).
   The Tahun button visually stands out from every filter next to it.

2. **Z-index bug.** `.budget-dropdown-content` (the popover panel that
   opens below the button) has `z-index: 10` (`budget.css:452`). The
   sticky header (`.navbar`) has `z-index: 100` and `position: fixed`
   (`style.css:79-86`). Since the header's stacking context wins, the
   popover's topmost option (e.g. "2026", the most recent year) renders
   underneath the header and becomes invisible/unclickable whenever the
   filter bar sits close enough to the top of the page for the two to
   overlap.

## Decision (confirmed with user)

Multi-year selection stays — the Tahun filter is not converted to a plain
single-select `<select>` (which would trivially dodge the z-index bug by
using the browser's own native popover, but would drop the ability to
filter by more than one year at once). Both problems are fixed while
keeping the existing checkbox-popover mechanism.

## Design

### Fix 1: Z-index

In `app/static/css/budget.css`, `.budget-dropdown-content`'s `z-index: 10`
becomes `z-index: 101` — one above the navbar's `100`, so the popover
always renders on top of the fixed header regardless of where the filter
bar sits on the page.

### Fix 2: Visual consistency

`.budget-dropdown-btn` (`budget.css:432-444`) is restyled to use the exact
same values as the global `input, select, textarea` rule
(`style.css:756-765`), so it's visually indistinguishable from a plain
`<select>` sitting next to it:

```css
.budget-dropdown-btn {
  background: #FFF;
  border: 1px solid var(--sl-300);
  color: var(--sl-900);
  border-radius: var(--r-md);
  padding: .375rem .6875rem;
  font-size: .8125rem;
  width: 100%;
  text-align: left;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: inherit;
  transition: border-color .12s, box-shadow .12s;
}
.budget-dropdown-btn:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(37,99,235,.09);
}
```

(A `:focus` state is added — plain `<select>`/`<input>` elements already
get one from the global rule; a `<button>` needs its own, matching
exactly, for the same keyboard-focus affordance.) `.budget-dropdown-check`,
`.budget-dropdown-content`, and its label styles are otherwise unchanged —
only the *trigger button* needed restyling to blend in; the popover
panel's own look (white background, border, shadow) already reads as a
normal dropdown panel and isn't part of what looked inconsistent.

### Scope

Both fixes live entirely in `budget.css`, which all three tabs
(`data.html`, `outstanding.html`, `report.html`) already link — one change
applies to all three since they share the same CSS classes for this
widget. No template or JS changes.

## Testing

- No frontend test framework exists for CSS-only changes (consistent
  precedent). Verification is manual: open each of Data/Outstanding/Report,
  open the Tahun dropdown, confirm every year option (including the
  topmost) is fully visible above the header, not clipped underneath it.
  Confirm the Tahun button's border/padding/font now visually matches the
  Cat/Pillar/Description `<select>` filters next to it and Payment
  Application's filter selects. Confirm multi-year checkbox selection
  still works exactly as before (pick 2+ years, confirm the table filters
  to the union).

## Out of Scope

- Converting Tahun to a native single-select `<select>` — explicitly
  declined; multi-year selection is a hard requirement.
- Unifying the `--bg-card`/`--border-color` vs `--sl-300`/`--r-md` token
  systems more broadly across the codebase — this spec only changes the
  one widget's literal values to match, not the underlying token
  architecture.
- Any change to Payment Application's own filter styling — it's already
  correct; this spec brings Sponsorship in line with it, not the reverse.
