# Sponsorship Report: month filter (Tgl Form) and export that follows the applied filter - Design

Date: 2026-10-06
Status: Draft for user review
Scope: page Sponsorship > Report (`/sponsorship/report`) of company Sinar Mas Tjipta (SMT) only. Dashboard, MR and other tabs are untouched.

## Goal
1. Add a **Bulan** filter (tick list, Jan-Des) to the Report, based on the same column as the existing Tahun filter: `tanggal_form_sponsor` (Tgl Form).
2. Rename the "Refresh" button label to **Terapkan Filter**.
3. The applied filter (Tahun + Bulan) holds for all four tabs: Include, BIB Include, Exclude, All.
4. Export Excel always equals what is applied on screen (tahun, bulan, active tab).

## Findings (current code)
- `static/js/sponsorship.js`: `sponsorshipReportState = {cat4, tahun}`; tab clicks reload with the stored state; the Refresh button copies the ticked years into the state; **the Export button reads the ticked checkboxes at click time** (not the applied state), so it can differ from the table when ticks are not applied yet.
- `modules/sponsorship/service.py`: `_apply_filters` filters years with `strftime('%Y', tanggal_form_sponsor)`; `get_sponsorship_report(company_id, tahun, cat4_mode)` uses it; result has `tahun`, `cat4_mode`, `sections`, `grand_total`, `pct_allocation`.
- `modules/sponsorship/routes.py`: `_parse_report_params()` -> `(tahun, cat4)` is used by `/api/report-data` and `/report/export`.
- `modules/sponsorship/exports.py`: `export_report_excel(company_id, tahun, cat4_mode)`; the title row text is `RANGKUMAN SPONSORSHIP {data['tahun']} - in Rp Full Amount`.
- Existing tests call `get_sponsorship_report(SMT, "2026", "all")` and `export_report_excel(SMT, ["2026"], "all")` positionally: the new parameter must be optional.

## Decisions (agreed with user)
- Bulan comes from Tgl Form (same column as Tahun). Tahun and Bulan combine with AND (years 2025+2026 and months Jan+Feb = Jan and Feb of both years).
- No month ticked = all months (today's behaviour). Defaults on page load: latest year, no month.
- Rows without a Tgl Form are excluded (as the year filter already does).
- Ticks take effect only when **Terapkan Filter** is pressed; switching tabs keeps the applied filter and never applies pending ticks silently.
- Filter state is not persisted across page reloads (unchanged).

## Design
### Service
- `_apply_filters`: new key `bulan` (list of two-digit strings `'01'..'12'`; a single value also accepted): `AND strftime('%m', tanggal_form_sponsor) IN (?,...)`.
- `get_sponsorship_report(company_id, tahun, cat4_mode, bulan=None)`: passes `bulan` into `filters` when non-empty; result gains `"bulan": [..]` (sorted two-digit strings) and `"bulan_label": "Jan, Feb"` (Indonesian short names Jan Feb Mar Apr Mei Jun Jul Agu Sep Okt Nov Des; `""` when none).
- Helper `month_label(bulan) -> str` (sorted, comma separated) shared by the report and the export.

### Routes
- `_parse_report_params()` returns `(tahun, cat4, bulan)`; `bulan` = the `bulan` query values that are `1..12` (accepted as `1` or `01`), normalised to two digits, de-duplicated, sorted; anything else is ignored.
- `/api/report-data` and `/report/export` pass `bulan` on. Export file name: `Sponsorship_Report_{cat4}_{years joined by -}[_{months joined by -}].xlsx`, e.g. `Sponsorship_Report_include_2026_01-02.xlsx`.

### Export
- `export_report_excel(company_id, tahun, cat4_mode, bulan=None)`; the title row becomes `RANGKUMAN SPONSORSHIP {tahun} ({bulan_label}) - in Rp Full Amount` when months are selected, otherwise unchanged. Both places that write this title use the same text.

### UI (`templates/sponsorship/report.html`, `static/js/sponsorship.js`)
- New dropdown `#sp-report-bulan-container` / `#sp-report-bulan` (class `budget-dropdown-check`, same markup as Tahun): twelve checkboxes `name="bulan"` with values `01..12` and labels Januari..Desember; none checked by default; button text `Bulan ▼`.
- Button `#sp-report-refresh`: label `Terapkan Filter` (id unchanged).
- JS: `sponsorshipReportState` gains `bulan`; `Terapkan Filter` copies the ticked years and months into the state and reloads; tab clicks reload with the state; **Export builds its query from the state** (`cat4`, `tahun`, `bulan`), not from the checkboxes.
- Empty-state text includes the months: `Belum ada data sponsorship untuk tahun 2026, bulan Jan, Feb.` (months part only when selected).

## Errors / edge cases
- Invalid `bulan` values (`13`, `0`, `abc`, empty) are ignored; if all are invalid it behaves as no month filter.
- Many values or duplicates are normalised; the query uses bound parameters.
- No data for the filter: the report shows the empty message; export still generates a file with the title and headers (as today).

## Testing
- Service: `bulan` filter in `get_sponsorship_report` for all four modes (`include`, `bib_include`, `exclude`, `all`), single and several months, combination with several years, rows without Tgl Form, no month = unchanged, result keys `bulan` / `bulan_label`.
- Export: title with and without months, rows follow the filter, empty result still produces a file.
- Routes: `/api/report-data?bulan=01&bulan=02`, invalid values ignored, `/report/export` follows `tahun`/`bulan`/`cat4` and the file name; page markup has the Bulan dropdown (12 boxes) and the label `Terapkan Filter`.
- Browser check on a throwaway instance with sample SMT transactions: Bulan dropdown, Terapkan Filter, tab switching keeps the applied filter, Export link/file equals the table.

## Out of scope
Month filter on the Sponsorship Dashboard, MR, Data and Outstanding pages; persisting the filter across reloads; month names other than the Indonesian short/long names above.
