# Management Report: Append data table and raw-data sheet - Design

Date: 2026-10-06
Status: Draft for user review
Builds on: the Management Report module (3 tabs, HO Report, two-sheet export; see `2026-10-05-management-report-ho-tabs-design.md`).

## Goal
1. Tab **Data Sync** shows the whole synced Append table (active snapshot) below the sync history, and can export it.
2. The per-CC export (Report menu: "Export CC ini" / "Export semua CC (ZIP)") gets a third sheet `Append` with the raw Append rows behind the Report.

## Decisions (agreed with user)
- Sheet 3 follows the Report filters: CC, YY, MM and COA (so its totals reconcile with sheet `Report`). All Cost Center = every row that passes the filters. In the ZIP each CC file carries its own rows.
- The Data Sync table is paged server-side (100 rows per page) with a CC filter and a text search; Export Append exports everything that passes those two filters (no filter = all rows).
- Visible and exportable by every logged-in user (like Report); data is per company from the active snapshot.

## 1. Data
`mr_append` already holds the rows. Columns shown/exported, in the order of sheet Append1:
`COA, MM, YY, CC, Category, Activity, Description, PTA, Custom, MM.1, ACT, BGT` (DB columns `coa, mm, yy, cc, category, activity, description, pta, custom, mm1, act, bgt`). Row order = insertion order (`id`), i.e. the order of the Excel sheet.

New service functions (`modules/management_report/service.py`):
- `query_append(company_id, cc=None, yy=None, mm=None, coas=None, q=None, limit=None, offset=0) -> {"rows": [dict], "total": int}`
  - filters on the active snapshot only (no snapshot -> empty); `cc=None` = all; `coas` empty = no COA filter; `q` = case-insensitive substring over `coa`, `category`, `activity`, `description`; `limit=None` = all rows.
  - row dict keys = the DB column names above.
- `append_cc_options(company_id) -> [cc]` is already available as `get_filter_options()["ccs"]` (reuse).

## 2. Data Sync tab UI
Section "Data Append" under "Riwayat sync" (inside the Data Sync tab, same card look as the sync card):
- Header: "Data Append (snapshot aktif)" and a summary "<total> baris" (of the current filter).
- Controls: CC dropdown (All Cost Center + CCs), search box (debounced 250 ms), button **Export Append (Excel)**.
- Table fragment (`budget-table` look as in the Report tab, wrapped in a `budget-page` scope; max height with its own scroll, sticky header): the 12 columns, PTA/ACT/BGT right-aligned in Indonesian number style (`1.234,5`), other columns left.
- Pager under the table: Sebelumnya / Berikutnya, "Halaman N dari M"; page resets to 1 when a filter changes.
- Loaded lazily: the first time the Data Sync tab is shown, then on every filter/page change, without page reload (fragment fetch with a per-request sequence number, loading dim like the other tabs). Empty snapshot: "Belum ada data. Sync dulu."

Routes (`routes.py`):
- `GET /management-report/append-table?cc=&q=&page=` -> HTML fragment `_append_table.html` (table + pager + count); `page` is 1-based, clamped to the valid range; unknown `cc` = all.
- `GET /management-report/append/export?cc=&q=` -> `Append.xlsx` (sheet `Append`), all rows passing the filters; 404 JSON when there are none.
Both use `jwt_html_required` and the session company.

## 3. Export sheet 3 `Append`
`exports.build_cc_workbook(report, filters=None, ho=None, append_rows=None)`: when `append_rows` is not None, add sheet `Append` after `HO Report`:
- Row 1: the 12 column headers (bold, light-grey fill, centered), freeze panes `A2`, auto-filter on the header row.
- Rows 2..n: values only. `COA`, `MM`, `YY`, `MM.1` are written as integers (in Append1 they are numeric; a COA that is not all digits is written as text), `PTA/ACT/BGT` as numbers with format `#,##0.0##`, the other columns as text; empty values stay empty cells.
- Column widths: COA 11, MM 5, YY 5, CC 14, Category 36, Activity 24, Description 70, PTA/ACT/BGT 12, Custom 8, MM.1 6.
- `exports.build_zip(reports, filters=None, ho_by_cc=None, append_by_cc=None)` passes each CC's rows.
- Routes `/export` and `/export-all` build `append_rows` with `service.query_append(company_id, cc, yy, mm, coas)` (all rows, `limit=None`); All Cost Center -> `cc=None`.
- A shared helper `exports.add_append_sheet(wb, rows, name="Append")` is used by both the per-CC workbook and the standalone Append export (`/append/export`, which builds a workbook with only that sheet).

## Errors / edge cases
- No active snapshot: the Data Append section shows the empty message; the fragment returns it with 200; `/append/export` returns 404 JSON; per-CC export is unaffected (it already needs data).
- `page` not a number or out of range -> clamped. `q` is escaped by Jinja; LIKE wildcards `%` and `_` in `q` are escaped so they match literally.
- Very long Description values are written as-is (Excel limit 32,767 chars is not reachable with this data).

## Testing
- Service: filters (cc, yy, mm, coas, q incl. literal `%`), paging (`limit`/`offset`, `total`), company isolation, no snapshot, order = insertion order.
- Routes: fragment (rows, pager text, page clamp, cc filter, search, empty state, login 302), export (sheet `Append`, header, row count, filters, 404 when empty, login).
- Export: sheet order `Report`, `HO Report`, `Append`; header row; freeze panes/auto-filter; the sum of `BGT` in sheet `Append` equals the Grand Total BGT of sheet `Report` (x1) for the same filters (and for All Cost Center); ZIP: every CC file has its own rows only.
- Browser check on a throwaway instance with the real master workbook: tab Data Sync shows the table (8,388 rows, 84 pages), CC filter and search refresh in place, Export Append downloads, per-CC export contains the third sheet.

## Out of scope
Editing rows, per-column sorting, YY/MM/COA filters on the Data Sync table, showing older snapshots' rows, Supabase sync.
