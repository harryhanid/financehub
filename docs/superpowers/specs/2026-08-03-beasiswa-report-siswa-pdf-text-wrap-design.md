# Beasiswa Report Siswa PDF — Text Wrap Fix — Design

## Problem

The "Laporan Siswa" PDF export (Beasiswa → Report Siswa tab → pick a student → export
as PDF, `GET /beasiswa/laporan/siswa/<code>/export/pdf` in
`app/modules/beasiswa/routes.py:611-779`) renders three of its five tables with plain
strings instead of wrapped text:

- **Data Siswa** (student info table) — values like Universitas, Fakultas, Nama
  Rekening, and Catatan (free-text notes) can be long.
- **IPK** table.
- **Rekapitulasi per Kategori** — the Kategori column.

`reportlab`'s `Table` with fixed `colWidths` does not wrap plain strings — a value
longer than its cell renders past the cell boundary and visually collides with the
neighboring cell's content. The other two tables in the same PDF (**Detail Budget**,
**Detail Payment**) already avoid this by wrapping every data cell in a `Paragraph`
via an existing `wrap_row()` helper (`routes.py:713-720`), which auto-wraps to the
column width. The three tables above were never migrated to that pattern.

## Goal

Make all text in the "Laporan Siswa" PDF wrap within its cell, matching the existing
Detail Budget/Detail Payment behavior, without regressing any of the three tables'
current visual formatting (bold labels, background tints, right-aligned currency
columns).

## Design

### Key constraint: `TableStyle` font/color rules don't apply to `Paragraph` cells

`reportlab.platypus.TableStyle` commands like `FONTNAME` and `TEXTCOLOR` only affect
cells whose content is a plain string/number — they have no effect on a cell whose
content is a `Paragraph` flowable, since a `Paragraph` renders its text using its own
`style` object. Any cell converted from a plain string to a `Paragraph` for wrapping
must therefore carry its own bold/color styling if it needs any; `TableStyle` rules
for `BACKGROUND`, `GRID`, and `VALIGN` are unaffected by this and continue to work
identically whether a cell holds a string or a `Paragraph`.

### Per-table treatment

| Table | Cells converted to `Paragraph` | Cells left as plain strings | Why |
|---|---|---|---|
| **Data Siswa** (`info_tbl`, a 2×(label, value) grid) | All cells — label columns (0, 2) get a new bold `label_style`; value columns (1, 3) get the existing `cell_style` | — | Every value column can hold long free text (Universitas, Fakultas, Nama Rek., Catatan). This table has no `ALIGN` override today, so wrapping every cell is safe. |
| **IPK** (`ipk_tbl`) | All cells — label column (0, "IPK Semester"/"IPK Penelitian") gets `label_style`; remaining columns get `cell_style` | — | Low practical risk (values are fixed-format like "Sem 1: 3.75"), but included for full consistency with the other tables per the confirmed scope ("semuanya"). |
| **Rekapitulasi per Kategori** (`sum_data`) | Only the **Kategori** column, in data rows only | Header row, the "TOTAL" footer row, and the 3 Rupiah columns (Budget/Payment/Selisih) in every row | The 3 Rupiah columns rely on `TableStyle`'s `ALIGN RIGHT` plus conditional red text for negative values — both are plain-string-only behaviors. Converting them to `Paragraph` would silently left-align them (a new visual regression) and would require re-implementing the conditional color inside each `Paragraph`'s style instead of via `TableStyle`, for no wrapping benefit (currency strings are always short). Header/TOTAL rows are fixed, short labels — no overflow risk. |

`wrap_row()` (used by Detail Budget/Detail Payment) is **not modified** — it already
does the right thing for those two tables (wraps data rows, leaves header/footer rows
as short plain strings), and this fix doesn't touch it.

### New style object

One new style, alongside the existing `cell_style` (`routes.py:708-711`):

```python
label_style = cell_style.clone('label_style')
label_style.fontName = 'Helvetica-Bold'
```

Used for the label columns in Data Siswa and IPK, replacing what `TableStyle`'s
`FONTNAME` commands did for those columns previously (those `FONTNAME` commands are
removed since they'd now be dead — superseded by `label_style`). The `BACKGROUND`
commands for those same columns stay unchanged, since `BACKGROUND` still works
correctly on `Paragraph` cells.

### Concrete changes

- `info_rows` (currently built as `[label, value, label, value]` plain-string rows,
  `routes.py:631-640`): each row's 4 items become
  `[Paragraph(label, label_style), Paragraph(value, cell_style), Paragraph(label, label_style), Paragraph(value, cell_style)]`
  (empty values render as `""`, matching `wrap_row()`'s existing empty-string handling).
- `info_tbl`'s `TableStyle` (`routes.py:642-652`): remove the two `FONTNAME` rules for
  columns 0 and 2; keep `BACKGROUND`, `GRID`, `VALIGN`, `TOPPADDING`, `BOTTOMPADDING`
  unchanged.
- `ipk_rows` (`routes.py:660-664`): column 0 becomes `Paragraph(label, label_style)`;
  the remaining columns in each row become `Paragraph(value, cell_style)`.
- `ipk_tbl`'s `TableStyle` (`routes.py:670-677`): remove the `FONTNAME` rule for
  column 0; keep the rest unchanged.
- `sum_data`'s data rows (`routes.py:683-684`, the loop building one row per
  `data["cat_summary"]` entry): column 0 (`c["cat1"]`) becomes
  `Paragraph(c["cat1"], cell_style)`; the 3 Rupiah columns stay plain
  `format_rupiah(...)` strings, unchanged. The header row (`routes.py:682`) and the
  `"TOTAL"` row (`routes.py:685-686`) are untouched.

## Testing

- No existing test covers this route today. Add a route-level smoke test
  (`GET /beasiswa/laporan/siswa/<code>/export/pdf` while logged in as ETF with a
  seeded student) asserting `200` and `mimetype == "application/pdf"` — this catches
  a crash (e.g. an unclosed `Paragraph`/`Table` construction bug) but cannot assert
  wrapped layout, since there's no PDF-content-inspection tooling in this codebase.
- Manual verification (required, since layout correctness can't be asserted by a
  test): seed or find a student with a long Universitas/Fakultas name and a long
  Catatan note, and a budget category with a long name, export to PDF, and confirm
  text wraps within its cell instead of overlapping the next cell — compare against
  the current (broken) PDF for the same student. Also confirm: label columns in Data
  Siswa/IPK still render bold with their grey background; the 3 Rupiah columns in
  Rekapitulasi per Kategori are still right-aligned and still show red text for
  negative Selisih.
- Run the full `pytest tests/` suite to confirm no regressions elsewhere — this
  change touches only one route in one module.

## Out of Scope

- Any change to Detail Budget/Detail Payment tables or `wrap_row()` — already correct.
- Any change to the CSV export path of the same route (`fmt == "csv"`, unaffected).
- Any change to PDF exports in other modules (Payment Memo, Sponsorship, Sahabat ETF,
  etc.) — this fix is scoped to the Beasiswa "Laporan Siswa" PDF only.
- Wrapping the header/TOTAL rows or the Rupiah value columns in Rekapitulasi per
  Kategori — deliberately excluded per the per-table treatment above, to avoid an
  alignment regression for no wrapping benefit.
