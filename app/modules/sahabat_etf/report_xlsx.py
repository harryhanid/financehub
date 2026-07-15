"""Sahabat ETF — 'REPORT PER [tanggal]' Excel export.

Replicates the legacy manually-maintained Book3.xlsx report layout using
openpyxl, computed entirely from modules.sahabat_etf.service.build_report_data()
(no Excel formulas — every value is a precomputed static number).
"""
import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

_INDO_MONTHS = ["", "JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI",
                "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]

_NAVY       = "1F4E79"
_DARK_NAVY  = "002060"
_GREEN      = "3C7D22"
_LIGHT_BLUE = "E3F6FD"
_WHITE      = "FFFFFF"

_FILL_NAVY       = PatternFill(start_color=_NAVY, end_color=_NAVY, fill_type="solid")
_FILL_DARK_NAVY  = PatternFill(start_color=_DARK_NAVY, end_color=_DARK_NAVY, fill_type="solid")
_FILL_GREEN      = PatternFill(start_color=_GREEN, end_color=_GREEN, fill_type="solid")
_FILL_LIGHT_BLUE = PatternFill(start_color=_LIGHT_BLUE, end_color=_LIGHT_BLUE, fill_type="solid")

_FONT_TITLE    = Font(bold=True, size=25)
_FONT_UNIT     = Font(bold=False, size=15)
_FONT_HEADER   = Font(bold=True, size=15, color=_WHITE)
_FONT_SECTION  = Font(bold=True, size=15, color=_WHITE)
_FONT_SUBTOTAL = Font(bold=True, size=15)
_FONT_NORMAL   = Font(bold=False, size=15)
_FONT_PILLAR   = Font(bold=True, size=15)

_ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
_ALIGN_LEFT   = Alignment(horizontal="left", vertical="center")
_ALIGN_RIGHT  = Alignment(horizontal="right")

_THIN   = Side(style="thin")
_MEDIUM = Side(style="medium")
_THICK  = Side(style="thick")
_BORDER_ROW = Border(top=_THIN, bottom=_THIN)

_MONEY_FMT = '_-* #,##0_-;\\-* #,##0_-;_-* "-"??_-;_-@_-'
_PCT_FMT   = "0.0%"

_COL = {
    "desc": "B", "periode_start": "C", "periode_dash": "D", "periode_end": "E", "pillar": "F",
    "cur_plafon": "G", "cur_klaim": "H", "cur_dibayar": "I", "cur_saldo": "J",
    "cum_plafon": "K", "cum_klaim": "L", "cum_dibayar": "M", "cum_saldo": "N",
    "catatan": "O",
}
_METRIC_COLS = {
    "cur": ["cur_plafon", "cur_klaim", "cur_dibayar", "cur_saldo"],
    "cum": ["cum_plafon", "cum_klaim", "cum_dibayar", "cum_saldo"],
}
_METRIC_KEYS = ["plafon", "klaim", "dibayar", "saldo"]


def _set(ws, coord, value, font=None, fill=None, align=None, border=None, numfmt=None):
    c = ws[coord]
    c.value = value
    if font:   c.font = font
    if fill:   c.fill = fill
    if align:  c.alignment = align
    if border: c.border = border
    if numfmt: c.number_format = numfmt
    return c


def _today_title() -> str:
    now = datetime.now()
    return f"{now.day} {_INDO_MONTHS[now.month]} {now.year}"


def _set_column_widths(ws):
    widths = {"A": 2.38, "B": 44.84, "C": 10.54, "D": 1.54, "E": 10.84,
              "F": 21.0, "G": 13.92, "O": 16.69}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def _write_title(ws, row):
    ws.merge_cells(f"B{row}:N{row}")
    _set(ws, f"B{row}", f"REPORT PER {_today_title()}", font=_FONT_TITLE, align=_ALIGN_LEFT)
    _set(ws, f"O{row}", "(Rp, Dalam Jutaan)", font=_FONT_UNIT, align=_ALIGN_RIGHT)
    return row + 2


def _write_header(ws, row, report_year):
    ws.merge_cells(f"B{row}:B{row+1}")
    _set(ws, f"B{row}", "Deskripsi", font=_FONT_HEADER, fill=_FILL_NAVY, align=_ALIGN_CENTER,
         border=Border(top=_MEDIUM, bottom=_MEDIUM, left=_MEDIUM))
    ws.merge_cells(f"C{row}:E{row+1}")
    _set(ws, f"C{row}", "Periode", font=_FONT_HEADER, fill=_FILL_NAVY, align=_ALIGN_CENTER,
         border=Border(top=_MEDIUM, bottom=_MEDIUM))
    ws.merge_cells(f"F{row}:F{row+1}")
    _set(ws, f"F{row}", "Pillar", font=_FONT_HEADER, fill=_FILL_NAVY, align=_ALIGN_CENTER,
         border=Border(top=_MEDIUM, bottom=_MEDIUM))
    ws.merge_cells(f"G{row}:J{row}")
    _set(ws, f"G{row}", f"TAHUN {report_year}", font=_FONT_HEADER, fill=_FILL_NAVY,
         align=_ALIGN_CENTER, border=Border(top=_MEDIUM, left=_THICK))
    ws.merge_cells(f"K{row}:N{row}")
    _set(ws, f"K{row}", f"S/D TAHUN {report_year}", font=_FONT_HEADER, fill=_FILL_GREEN,
         align=_ALIGN_CENTER, border=Border(top=_MEDIUM))
    ws.merge_cells(f"O{row}:O{row+1}")
    _set(ws, f"O{row}", "Catatan", font=_FONT_HEADER, fill=_FILL_NAVY, align=_ALIGN_CENTER,
         border=Border(top=_MEDIUM, bottom=_MEDIUM, right=_MEDIUM))

    sub_row = row + 1
    for label, col in (("Plafon", "G"), ("Klaim", "H"), ("Dibayar", "I"), ("Saldo", "J")):
        _set(ws, f"{col}{sub_row}", label, font=_FONT_HEADER, fill=_FILL_NAVY,
             align=_ALIGN_CENTER, border=Border(bottom=_MEDIUM))
    for label, col in (("Plafon", "K"), ("Klaim", "L"), ("Dibayar", "M"), ("Saldo", "N")):
        _set(ws, f"{col}{sub_row}", label, font=_FONT_HEADER, fill=_FILL_GREEN,
             align=_ALIGN_CENTER, border=Border(bottom=_MEDIUM))
    return row + 2


def build_report_workbook(data: dict) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"
    _set_column_widths(ws)

    row = _write_title(ws, 1)
    row = _write_header(ws, row, data["report_year"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
