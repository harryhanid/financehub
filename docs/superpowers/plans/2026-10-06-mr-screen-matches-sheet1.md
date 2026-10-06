# Management Report: Report tab on screen matches sheet 1 - Design and Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement. Steps use checkbox syntax.

**Goal:** The Report tab on screen shows exactly what sheet 1 ("BGT Report per CC") of the export contains, so that for the same filters (CC, YY, MM, COA, Category) the screen, sheet 1 and the export agree. HO Report (tab and sheet 2) and Append (sheet 3) stay as they are.

**Why (evidence):** with CC POCPRO, YY 26, MM 8 the screen showed Budget 44,9 / Actual 9,5 (month 8 only) while sheet 1 showed Budget YTD 612,9 / Actual YTD 277,3 (full year + YTD to Period). With 5 COAs ticked the screen said "Tidak ada data" while sheet 1 had data. The user chose: "layar dan sheet 1 harus kembar".

## Design
- The Report tab renders the `bgt` dict produced by `routes._bgt_for(...)` (`build_bgt_report`): MM is the **Period** (year to date), not an exact month; YY/COA/Category filter the lines as in sheet 1.
- Columns (Rp Mio, Indonesian number style via `mr_num`/`mr_pct`): Description | Budget Full Year | Budget YTD | PTA YTD | Budget Available YTD | Actual YTD | Var Amount | Var % | Available Bgt Amount | Available Bgt %.
- Rows: OPEX / CAPEX level rows (strong background), category rows (lighter background, a toggle arrow, click toggles its detail rows), detail rows (`- Bgt 2026 : ... Month : n`, COA shown, collapsed by default). Two links above the table: "Buka semua" / "Tutup semua". No grand total row (sheet 1 has none).
- Header line above the table: report title, `In Rp Mio`, and `Period <Mon yyyy> (YTD)`.
- Empty state text unchanged: `Tidak ada data untuk filter ini.` (shown when `bgt` is missing or `bgt.has_data` is false).
- The detail rows are shown/hidden by event delegation in `index.html` (the fragment is injected with innerHTML, scripts inside it do not run).
- `routes._report_for` is replaced by a function that returns the `bgt` dict (with `title`, `cc_code`, `cc_desc`) or `None` when no CC; `index()` and `/table` pass it to the template as `bgt`. `export_one` / `export_all` keep their current logic.
- The old Report-table template markup and its on-screen tests are replaced; `service.build_report` stays (export gating and legacy sheet use it).

## Global Constraints
- Do NOT run git add/commit/stash/checkout for code files (the tree has the user's uncommitted work). Edit with Edit/Write tools only. Never touch port 8081.
- Keep line endings of each file (templates/routes are LF).
- Run tests from `C:\Financehub\app`.

## Task 1: Screen = sheet 1

**Files:** modify `app/modules/management_report/routes.py`, `app/templates/management_report/_report_table.html`, `app/templates/management_report/index.html` (JS + CSS + include variable name), tests `app/tests/test_mr_routes.py` (and any other test asserting the old Report table markup).

- [ ] **Step 1: Tests first.** In `tests/test_mr_routes.py` replace the old on-screen assertions (`"06 - Gift Total"`, `"Grand Total"`, `"-79,1%"`, `"Gift A"` etc. in `test_page_shows_report_for_selected_cc` and the ~line 296 test) by tests that fail now and describe the new screen. Data: two CC rows with months 1 and 9, `period` meta `2026-08-31`. Required assertions (via `/management-report/table?cc=...` and the full page):
  - the table contains `Budget Full Year`, `Budget YTD`, `Actual YTD`, `OPEX`, the category name without its `NN - ` prefix, and the full-year budget (all months) while Budget YTD excludes month 9 (Indonesian formatting, e.g. `16,0` vs `10,0`);
  - detail rows exist in the HTML but are hidden (attribute `hidden`) and carry the text `- Bgt 2026 :`;
  - `mm=10` changes the YTD but not the full year; `cat=` / `coa=` filters remove the other category's rows; a COA subset with data only in other months still shows rows (no "Tidak ada data");
  - a page/table with `yy=1999` shows `Tidak ada data untuk filter ini.`;
  - screen numbers equal sheet 1: for the same query, parse `D10`..`I10` of `/export?...` sheet 1 and compare with the OPEX row of `/table?...` (format with the same Indonesian style or compare via `bgt` data).
  Run them and see them fail.
- [ ] **Step 2: Routes.** Replace `_report_for` so it returns `_bgt_for(...)` data enriched with `title`/`has_data` (None when `filters["cc"]` is None); use it in `index()` and `table()` as `bgt=`; keep `report` available only if other templates need it. `_bgt_for` already provides `title` param: reuse `_report_title`.
- [ ] **Step 3: Template.** Rewrite `_report_table.html` for `bgt` per the design (CSS classes `mr-lvl-row`, `mr-cat-row`, `mr-detail`; detail rows `hidden`; `data-g` index linking category rows and their details; toggle arrow via CSS or text). Add a small CSS block in `index.html` for the new row classes; add delegated click handling on `#mr-report` (toggle a category's detail rows) and the "Buka semua" / "Tutup semua" links (these links live inside the fragment, so also handle them by delegation).
- [ ] **Step 4: Run** `python -m pytest tests/test_mr_routes.py tests/test_mr_exports.py tests/test_mr_bgt_exports.py tests/test_mr_bgt_report.py tests/test_mr_ho_report.py tests/test_mr_report.py tests/test_mr_service.py tests/test_dashboard.py -q`, all must pass. Run `node --check` on the extracted inline script as the previous work did (Jinja expressions replaced by placeholders).
- [ ] **Step 5: Report** (no commit) to `C:\Financehub\.superpowers\sdd\task-5-report.md`.
