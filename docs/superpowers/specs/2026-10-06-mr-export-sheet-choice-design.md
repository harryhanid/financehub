# Management Report: choose which sheets to export - Design

Date: 2026-10-06
Status: Draft for user review
Scope: the export buttons of the Management Report Report/HO tabs (`index.html`, `routes.py`). Sheet contents are unchanged.

## Goal
One **Export semua CC (ZIP)** button (the "tanpa Append" button goes away) and an **Export CC ini** button; clicking either asks which sheets to download:
- **Sheet 1 saja** (BGT Report per CC)
- **Sheet 1 + 2** (BGT Report per CC + BGT HO Report per CC)
- **Semua** (Sheet 1 + 2 + 3 Append) - default

## Behaviour
- Click on either button opens a small popover under the button with three radio options, a **Download** and a **Batal** button. Esc or a click outside closes it. The last choice is remembered per browser (localStorage, wrapped in try/catch; the page works without it); default `Semua`.
- Download navigates to the button's current export URL (which already carries cc/yy/mm/coa/cat and is refreshed whenever a filter changes) with `sheets=<1|12|123>` added.
- All filters keep applying for every choice.

## Backend
- `routes._sheets()` reads `sheets` (allowed values `1`, `12`, `123`); a missing or invalid value means `123` (old behaviour). For `export-all` the legacy `append=0` maps to `12` when `sheets` is absent.
- `export_one` / `export_all` build the HO report only when `2` is requested and the Append rows only when `3` is requested (nothing extra is computed for "Sheet 1 saja"); they pass `ho=None` / `append_rows=None` otherwise. `exports.build_cc_workbook` / `build_zip` need no change (they already skip those sheets for `None`).
- ZIP file name: `Management Report <date>.zip` for all sheets, `... sheet 1.zip` and `... sheet 1-2.zip` otherwise (replaces the `tanpa Append` suffix). The single-CC file stays `<CC>.xlsx`.
- The 404 gates stay as they are (they depend on the report/sheet 1 data, not on the chosen sheets).

## Frontend
- Remove `#mr-export-all-lite` and its JS. `#mr-export-one` and `#mr-export-all` stay anchors (their `href` is still refreshed by the filter script); a click is intercepted (`preventDefault`) to open the popover for that anchor; Download sets `location.href = anchor.href + (anchor.href.includes('?') ? '&' : '?') + 'sheets=' + value`.
- The popover is one shared element in the filter bar (`#mr-export-pop`), positioned under the clicked button, styled with the existing `budget-card`/`budget-btn` look.

## Testing
- Routes: single CC and ZIP for `sheets=1`, `12`, `123` (sheet names per workbook, ZIP name suffix), invalid `sheets` falls back to all, legacy `append=0` still gives sheets 1 and 2, `sheets=1` does not read HO/Append (sheet names only).
- Page: exactly one ZIP button, no `mr-export-all-lite`, popover markup with the three options and Download/Batal; the old test for the "tanpa Append" button is replaced.
- Browser check on a throwaway instance: both buttons open the popover, the chosen option ends up in the URL, Esc/Batal closes, filter changes still update the links.

## Out of scope
Per-sheet selection beyond the three fixed options; the Data Sync tab's Append export button.
