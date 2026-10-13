"""HO Report sheet of the per-CC export; mirrors 'BGT HO Report per CC' of the Excel master."""
from datetime import date

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from modules.management_report.formatting import id_number

_BLUE = "0000FF"
_NUM = '_(* #,##0_);_(* (#,##0);_(* "-"_);_(@_)'
_CODE = "000-00-000"
_HEAD = PatternFill("solid", fgColor="FFCC99")
_GREEN = PatternFill("solid", fgColor="7CEB99")
_AMOUNT = PatternFill("solid", fgColor="CCFFFF")
_MED = Side(style="medium")
_THIN = Side(style="thin")
_WIDTHS = {"A": 17.2, "B": 52, "C": 8.5, "D": 16, "E": 14, "F": 16, "G": 30}
_KEYS = (("bgt", "BGT"), ("pta", "PTA"), ("act", "ACT"))


def _font(size=11, bold=False, color=None, italic=False):
    return Font(name="Arial", size=size, bold=bold, color=color, italic=italic)


def _frame(ws, r, summary, top=None, bottom=None):
    """Reference borders: medium frame at the sides of the table, thin inside the summary section."""
    inner = _THIN if summary else _MED
    for col in range(1, 7):
        left = _MED if col == 1 else (inner if col >= 4 else None)
        right = _THIN if col == 1 else (inner if col >= 4 else None)
        ws.cell(r, col).border = Border(left=left, right=right, top=top, bottom=bottom)


def _header(ws, r, summary, period):
    top = {1: "Nomor" if summary else "GL Account", 2: "Keterangan" if summary else "Description",
           4: "Budget", 5: "PTA", 6: "Actual"}
    sub = {1: "Prakiraan" if summary else None, 4: period, 5: period, 6: period}
    for col in range(1, 7):
        for row, vals in ((r, top), (r + 1, sub)):
            c = ws.cell(row, col, vals.get(col))
            c.font = _font(bold=True)
            c.fill = _HEAD
            c.alignment = Alignment(horizontal="center")
    for row in (r, r + 1):
        for col in (2, 3):
            ws.cell(row, col).alignment = Alignment(horizontal="centerContinuous")
    _frame(ws, r, summary, top=_MED)
    _frame(ws, r + 1, summary, bottom=_MED)
    return r + 2


def _amounts(ws, r, row, fill=None, bold=False, color=None):
    for col, key in zip((4, 5, 6), ("bgt", "pta", "act")):
        c = ws.cell(r, col, row[key])
        c.number_format = _NUM
        c.font = _font(bold=bold, color=color)
        c.alignment = Alignment(horizontal="right")
        if fill is not None:
            c.fill = fill


def _amount_text(item) -> str:
    parts = [f"{name} {id_number(item[key], 0)}" for key, name in _KEYS if item[key]]
    return " / ".join(parts) if parts else "0"


def _footnote(ws, r, text) -> int:
    c = ws.cell(r, 1, text)
    c.font = _font(size=9, italic=True, color="666666")
    return r + 1


def add_ho_sheet(wb, ho) -> None:
    """Append sheet 'BGT HO Report per CC' (values only) built from a build_ho_report() result."""
    ws = wb.create_sheet("BGT HO Report per CC")
    for r, text, size in ((1, ho["org"], 16), (2, ho["location"], 12), (3, "MD:", 12),
                          (4, f"Division/Dept.: {ho['division']}", 12)):
        c = ws.cell(r, 1, text)
        c.font = _font(size=size, bold=True, color=_BLUE)
    period = ho.get("period")
    if period:
        try:
            ws["G2"] = date.fromisoformat(str(period)[:10])
            ws["G2"].number_format = "dd-mmm-yy"
            ws["G2"].font = _font()
            ws["G2"].fill = _GREEN
        except ValueError:
            pass
    ws["G3"] = ho.get("cc") or "All"
    ws["G3"].data_type = "s"
    ws["G3"].font = _font()
    ws["G3"].fill = _GREEN

    r = 6
    for section in ho["sections"]:
        summary = section["key"] == "summary"
        title = ws.cell(r, 1, section["title"])
        title.font = _font(bold=True)
        r = _header(ws, r + 1, summary, ho["period_label"])
        for row in section["rows"]:
            kind = row["type"]
            total = kind not in ("group", "account") and not (summary and not row["grand"])
            if kind == "group":
                ws.cell(r, 1, row["label"]).font = _font(bold=True)
            elif kind == "account":
                code = ws.cell(r, 1, int(row["code"]))
                code.number_format = _CODE
                code.font = _font()
                code.alignment = Alignment(horizontal="center")
                ws.cell(r, 2, row["label"]).font = _font()
                _amounts(ws, r, row, fill=_AMOUNT)
                if row.get("note"):
                    ws.cell(r, 7, row["note"]).font = _font(color="003366")
            elif summary and not row["grand"]:
                nomor = ws.cell(r, 1, row["nomor"])
                nomor.font = _font()
                nomor.alignment = Alignment(horizontal="center")
                ws.cell(r, 2, row["label"]).font = _font()
                _amounts(ws, r, row)
            else:                                    # group total or grand total
                ws.cell(r, 2 if summary else 1, row["label"]).font = _font(bold=True, color=_BLUE)
                _amounts(ws, r, row, bold=True, color=_BLUE)
                side = _MED if row.get("grand") else _THIN
                _frame(ws, r, summary, top=side, bottom=side)
                if not summary:
                    for col in (1, 2, 3):
                        ws.cell(r, col).alignment = Alignment(horizontal="centerContinuous")
            if not total:
                _frame(ws, r, summary)
            r += 1
        if section["key"] == "opex":
            for u in ho["unmapped"]:
                label = f" ({u['label']})" if u["label"] else ""
                r = _footnote(ws, r, f"Tidak termasuk COA {u['coa']}{label}: {_amount_text(u)}")
        if summary:
            for m in ho["summary_missing"]:
                r = _footnote(ws, r, f"Tidak ada di ringkasan: akun {m['coa']} ({m['label']}): "
                                     f"{_amount_text(m)} (termasuk di Grand Total Opex)")
        r += 2

    for col, width in _WIDTHS.items():
        ws.column_dimensions[col].width = width
