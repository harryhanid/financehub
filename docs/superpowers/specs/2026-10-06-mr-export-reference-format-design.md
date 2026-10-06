# Management Report export: sheet 1 and sheet 2 in the reference format - Design

Date: 2026-10-06
Status: Draft for user review
Scope: the per-CC Excel export of Management Report (`exports.py`, `ho_exports.py`). On-screen tabs (Report, HO Report, Data Sync) and the Append sheet are untouched.
Reference file: `C:\Users\25010160\Downloads\Report YTD Aug 2025 - POCPRO.xlsx` (sheets "BGT Report per CC" and "BGT HO Report per CC").

## Goal
1. Sheet 1 of the export looks and is structured like the reference "BGT Report per CC".
2. Sheet 2 of the export looks like the reference "BGT HO Report per CC" (content is already equal, styling is not).
3. Sheet 3 (Append) stays as it is.

## Approach
Rebuild with openpyxl and copy the reference styles (fonts, fills, borders, widths, number formats, merges) into constants. Rejected: using the reference file as a template and filling cells, because the number of rows differs per CC.

## Sheet 1 - "BGT Report per CC"
Sheet name changes from `Report` to `BGT Report per CC`. Zoom 70%. Font Aptos Narrow. Values are numbers (no formulas), in Rp Mio.

### Header (rows 1-8)
- C1:O1 merged, centred, bold 20: report title (same text as today: `President Office & ETF – <CC description>`). Row height 26.
- C2:O2 merged, centred, bold 20: `In Rp Mio`. A2 = CC code, A3 = `<company short code> - <CC description>` (e.g. `SMT - Creative & Production`), bold, light-blue fill (A:B), height 26.
- Row 4: C4 `Period:`, D4 = period date (end of month, format `mmm-yy`), bold 12, light-yellow fill.
- Row 5: column numbers, bold 12, centred: D `1`, E `2`, F `3`, G `4\n( 2 + 3 )`, I `5`, J `( 5 - 4 )`, K `( 5 - 4 ) / 4`, M `( 1 - 5 )`, N `( 1 - 5 ) / 1`. Height 32.
- Rows 6-8: blue header `#538DD5`, white bold 11, centred, merges as in the reference: C6:C8 `Description`; D6:G6 `Consolidation Budget`; I6:K6 `Consolidation Actual`; M6:N7 `Available Bgt YTD <yy> - Actual <Mon yy>`; O6:O8 `Remarks`; row 7 sub headers `Budget YTD` (D), `Budget YTD` (E), `PTA YTD`, `Budget Available YTD\n(Budget + PTA)`, `Actual YTD`, J7:K7 `Var A <Mon yy> to B <Mon yy>`; row 8 period date (`mmm-yy`) over E, F, G, I, `Amount`/`%` over J-K and M-N. Heights 16 / 43.5 / 16. Columns H and L are narrow spacers.

### Columns (amounts in Rp Mio, number format `_(* #,##0_);_(* \(#,##0\);_(* "-"??_);_(@_)`, percent `0.0%` on OPEX/CAPEX rows and `0%` elsewhere)
| Col | Content |
| --- | --- |
| C | description |
| D | Budget full year: sum of BGT, all months of the year |
| E | Budget YTD: BGT of months 1..Period month |
| F | PTA YTD: PTA of months 1..Period month |
| G | Budget Available YTD = E + F |
| I | Actual YTD: ACT of months 1..Period month |
| J | Var amount = I - G |
| K | Var % = J / G (blank when G = 0) |
| M | Available Bgt = D - I |
| N | Available % = M / D (blank when D = 0) |
| O | Remarks: header only, cells empty |
Widths: A 8.4, B 11.7, C 59.3, D 11.5, E 10.9, F 12.8, G 19.9, H 1.4, I 11.4, J 10.8, K 11.7, L 1.3, M 11.2, N 11.7, O to be wide enough for the word `Remarks` (reference value kept if present).

### Body rows
- Starts at row 9 (row 9 is the helper row `fltr` in column A in the reference; it is not reproduced).
- **Level rows** `OPEX` then `CAPEX` (only those that have data): bold, fill `#95B3D7`, label in C.
- **Category header rows** (the Append `Category`, shown with its name): bold, fill `#CCECFF`, amounts bold, outline level 0.
- **Detail rows**, one per Append line of that category, outline level 2 and **hidden** (collapsed, +/- symbols on the left; `summaryBelow=False` so the +/- sits on the header row):
  - COA in column B.
  - Text in C: `- Bgt <yy> : <description> Month : <mm1>` for a row with a BGT amount, `- Pta <yy> : ...` for PTA, `- Act <yy> : ...` for ACT. A line with several of the amounts produces one detail row per amount type.
  - Amounts go only in the matching column(s): Bgt line -> D, and E when its month is within YTD; Pta line -> F; Act line -> I.
- Level and category order follow the existing on-screen Report (same ordering as `build_report`).
- OPEX or CAPEX: a category's COA (first COA of its lines) that is in the Capex section of `ho_template.json` (27xxxxxxx) -> CAPEX, otherwise OPEX. Level row amounts are the sums of its categories.

### Period
- Period month = the `mm` filter when one month is selected; otherwise the latest month that has data for the chosen year. Year = the `yy` filter, else the latest year in the data. Period date = last day of that month.
- Budget full year and all YTD columns use that one year.

## Sheet 2 - "BGT HO Report per CC"
Sheet name changes from `HO Report` to `BGT HO Report per CC`. Rows, labels and amounts stay as built by `ho_report.py`; only the styling follows the reference:
- Font Arial 11 everywhere except title lines (A1 bold 16 indexed-blue as in reference, A2/A3 bold 12, A4 bold 12 and B4 bold 11 blue `0000FF`).
- F1: `Note : Untuk melihat detail actual ada di kolom C ...` text from the reference, bold; G2 period date with fill `#7CEB99` (`dd-mmm-yy`), G3 CC code with fill `#7CEB99`.
- Table header rows: bold, centred, grey/lavender fill taken from the reference (`idx47`), box borders (left/right/top/bottom as in the reference), `centerContinuous` for the Description cell.
- Account rows: GL code centred with format `000\-00\-000`, description left, amount cells right aligned with fill `#CCFFFF` and left/right borders.
- `Total - ...` rows: bold, border on all sides, `centerContinuous` label.
- Column widths: A 17.2, B 52, D 15.9, E 9.8, F 10.8, G 10.4, H 11.2, I 10.2, J 9.3.
- Footnotes about unmapped COA / summary-missing accounts stay (small italic) below their section.

## Sheet 3 - "Append"
Unchanged.

## Edge cases
- No data for the CC: sheet 1 header is written, body empty (no OPEX/CAPEX rows).
- Month filter set to a month without data: Period shows that month, YTD columns are zeros where there is nothing.
- Division by zero in K / N: cell left empty.
- Text values that begin with `=`: written as plain strings (existing escaping behaviour must not regress).
- ZIP export: every CC workbook uses the same builder.

## Testing
- Unit: sheet names, header texts/merges, column widths, number formats, key fills (`538DD5`, `95B3D7`, `CCECFF`, `CCFFFF`, `7CEB99`), outline level 2 + hidden for detail rows, first visible rows are level/category rows.
- Numbers: with a fixture, D/E/F/G/I/J/M and the two percentages equal hand-computed values; OPEX/CAPEX totals equal the sum of categories; Period default (latest month) and `mm` filter override; YTD excludes later months.
- Sheet 2: styling checks on a few cells (font name, fills, borders, merged/`centerContinuous`), values identical to the current output.
- Regression: existing `test_mr_*` suite adjusted only where it asserts the old sheet 1 layout/sheet names.
- Manual comparison: export the same CC/period as the reference and compare styles side by side.

## Out of scope
On-screen tab styling; formulas in exported cells; the Remarks column content; changes to Append data or sync.

## Adjustments agreed while planning (override the text above where they differ)
- **Period default:** the `mm` filter if set; otherwise the snapshot's report period (`Parameter!B2`, stored in the sync metadata) when it is in the chosen year; otherwise the latest month that has ACT; otherwise 12. ("Latest month with data" is not usable because budget lines exist for every month.)
- **YTD month of a line** is `mm1`, falling back to `mm`; a line without a month counts as within YTD.
- **CAPEX** is decided by COA starting with `27` (not by lookup in the HO template), everything else is OPEX.
- **Header cell D7** reads `Budget Full Year` (the reference text `Budget YTD` is wrong for that column).
- **Sheet 1 body** starts at row 10 (row 9 stays empty, as the reference helper row `fltr` is not reproduced). Category names drop their `NN - ` prefix.
- **Sheet 2:** the `Note : ... sheet Consol` cell F1 is not written (that sheet does not exist in our export). Columns E and F are kept at 14 and 16 wide (instead of 9.8 / 10.8) so Rp 000 amounts do not show `#####`. G2 = period date, G3 = CC code (`All` for All Cost Center).
- **Legacy callers:** `build_cc_workbook` without the new `bgt` argument still produces the old `Report` first sheet.
