# modules/sponsorship/exports.py
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from modules.sponsorship.service import get_sponsorship_report, PILLAR_COLUMNS

_HEADER_FILL = PatternFill("solid", fgColor="1E3A5F")
_HEADER_FONT = Font(color="FFFFFF", bold=True)
_SECTION_FILL = PatternFill("solid", fgColor="FEF9C3")
_SECTION_FONT = Font(bold=True, color="854D0E")
_GRANDTOTAL_FILL = PatternFill("solid", fgColor="1E3A5F")
_GRANDTOTAL_FONT = Font(color="FFFFFF", bold=True)
_NUM_FMT = "#,##0"

_COLUMN_LABELS = ["NO", "LEMBAGA / PERORANGAN", "PERIHAL"] + list(PILLAR_COLUMNS.keys()) + ["TOTAL"]


def export_report_excel(company_id: int, tahun: str, cat4_mode: str) -> bytes:
    data = get_sponsorship_report(company_id, tahun, cat4_mode)
    pillar_cols = list(PILLAR_COLUMNS.values())

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"

    ws.append([f"RANGKUMAN SPONSORSHIP {data['tahun']} - in Rp Full Amount"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([])

    def _write_column_header():
        ws.append(_COLUMN_LABELS)
        row = ws.max_row
        for col in range(1, len(_COLUMN_LABELS) + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT

    if not data["sections"]:
        _write_column_header()

    for section in data["sections"]:
        _write_column_header()

        ws.append([section["description"].upper()])
        row = ws.max_row
        ws.cell(row=row, column=1).fill = _SECTION_FILL
        ws.cell(row=row, column=1).font = _SECTION_FONT

        for r in section["rows"]:
            ws.append(
                [r["no"], r["lembaga_perorangan"], r["perihal"] or ""] +
                [r[col] for col in pillar_cols] + [r["total"]]
            )
            row = ws.max_row
            for col in range(4, len(_COLUMN_LABELS) + 1):
                ws.cell(row=row, column=col).number_format = _NUM_FMT
            ws.cell(row=row, column=2).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=row, column=3).alignment = Alignment(wrap_text=True, vertical="top")

        sub = section["subtotal"]
        ws.append(
            [f"TOTAL {section['description'].upper()}", "", ""] +
            [sub[col] for col in pillar_cols] + [sub["total"]]
        )
        row = ws.max_row
        for col in range(1, len(_COLUMN_LABELS) + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = _SECTION_FILL
            cell.font = _SECTION_FONT
            if col >= 4:
                cell.number_format = _NUM_FMT

    gt = data["grand_total"]
    ws.append(
        ["TOTAL SPONSORSHIP (ACTUAL)", "", ""] +
        [gt[col] for col in pillar_cols] + [gt["total"]]
    )
    row = ws.max_row
    for col in range(1, len(_COLUMN_LABELS) + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = _GRANDTOTAL_FILL
        cell.font = _GRANDTOTAL_FONT
        if col >= 4:
            cell.number_format = _NUM_FMT

    pct = data["pct_allocation"]
    ws.append(["% Allocation", "", ""] + [f"{pct[col]}%" for col in pillar_cols] + [""])

    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 45
    ws.column_dimensions["C"].width = 60
    for col_letter in ("D", "E", "F", "G", "H"):
        ws.column_dimensions[col_letter].width = 16

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
