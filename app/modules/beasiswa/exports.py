# modules/beasiswa/exports.py
import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from modules.beasiswa.service import (
    get_dashboard_pillar_yearly,
    get_dashboard_trend_transactions,
)

# --- Styling Constants ---
FONT_FAMILY = "Calibri"

FONT_MAIN_TITLE = Font(name=FONT_FAMILY, size=14, bold=True, color="0F766E")
FONT_SUBTITLE = Font(name=FONT_FAMILY, size=10, italic=True, color="475569")
FONT_META = Font(name=FONT_FAMILY, size=9, color="64748B")

FONT_HEADER = Font(name=FONT_FAMILY, size=11, bold=True, color="FFFFFF")
FILL_HEADER = PatternFill("solid", fgColor="0F766E")  # Teal / Emerald

FONT_ROW = Font(name=FONT_FAMILY, size=10)
FONT_ROW_BOLD = Font(name=FONT_FAMILY, size=10, bold=True)
FILL_ROW_ALT = PatternFill("solid", fgColor="F8FAFC")
FILL_TOTAL = PatternFill("solid", fgColor="ECFDF5")

ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")

THIN_BORDER_SIDE = Side(style="thin", color="CBD5E1")
DOUBLE_BOTTOM_SIDE = Side(style="double", color="0F766E")

BORDER_DATA = Border(
    left=THIN_BORDER_SIDE,
    right=THIN_BORDER_SIDE,
    top=THIN_BORDER_SIDE,
    bottom=THIN_BORDER_SIDE,
)

BORDER_TOTAL = Border(
    left=THIN_BORDER_SIDE,
    right=THIN_BORDER_SIDE,
    top=THIN_BORDER_SIDE,
    bottom=DOUBLE_BOTTOM_SIDE,
)

NUM_FMT_CURRENCY = '#,##0;(#,##0);"-"'


def export_dashboard_trend_tahunan_excel(
    company_id: int,
    years: list = None,
    pillars: list = None,
    programs: list = None,
    jenjangs: list = None,
    statuses: list = None,
    angkatans: list = None,
) -> bytes:
    wb = openpyxl.Workbook()

    # -------------------------------------------------------------
    # 1. SHEET 1: Trend per Tahun
    # -------------------------------------------------------------
    ws1 = wb.active
    ws1.title = "Trend per Tahun"
    ws1.views.sheetView[0].showGridLines = True

    yearly_data = get_dashboard_pillar_yearly(
        company_id,
        pillars=pillars,
        programs=programs,
        jenjangs=jenjangs,
        statuses=statuses,
        angkatans=angkatans,
        years=years,
    )
    # Sort chronologically ascending (e.g. 2014, 2015, ..., 2026)
    yearly_data = sorted(yearly_data, key=lambda x: x["tahun"])

    # Determine all distinct pillar names across rows
    pillar_set = set()
    for row in yearly_data:
        pillar_set.update(row["pillars"].keys())
    # Sort pillars alphabetically, but keep common ones nicely ordered
    known_order = ["AGRI", "APP", "ENERGY & FINANCE", "FINANCE", "EFIN", "LAND", "PROPERTY", "SETF"]
    sorted_pillars = sorted(
        list(pillar_set),
        key=lambda p: (known_order.index(p) if p in known_order else 99, p),
    )

    # Title block
    ws1["A1"] = "TREND REALISASI BEASISWA PER TAHUN"
    ws1["A1"].font = FONT_MAIN_TITLE
    ws1["A2"] = "Eka Tjipta Foundation (ETF)"
    ws1["A2"].font = FONT_SUBTITLE

    filter_desc = []
    if years:
        filter_desc.append(f"Tahun: {', '.join(str(y) for y in sorted(years))}")
    if pillars:
        filter_desc.append(f"Pillar: {', '.join(pillars)}")
    if programs:
        filter_desc.append(f"Program: {', '.join(programs)}")
    if jenjangs:
        filter_desc.append(f"Jenjang: {', '.join(jenjangs)}")
    if angkatans:
        filter_desc.append(f"Angkatan: {', '.join(str(a) for a in angkatans)}")
    if statuses:
        filter_desc.append(f"Status: {', '.join(statuses)}")
    
    ws1["A3"] = f"Filter: {'; '.join(filter_desc) if filter_desc else 'Semua Data'}"
    ws1["A3"].font = FONT_META
    ws1["A4"] = f"Tanggal Unduh: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    ws1["A4"].font = FONT_META

    # Table headers
    headers1 = ["No", "Tahun"] + sorted_pillars + ["Total Realisasi (Rp)"]
    start_row = 6
    ws1.row_dimensions[start_row].height = 24

    for col_idx, h in enumerate(headers1, 1):
        cell = ws1.cell(row=start_row, column=col_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER_DATA

    curr_row = start_row + 1
    for no, row in enumerate(yearly_data, 1):
        ws1.row_dimensions[curr_row].height = 20
        is_alt = (no % 2 == 0)
        row_fill = FILL_ROW_ALT if is_alt else None

        # No
        c_no = ws1.cell(row=curr_row, column=1, value=no)
        c_no.alignment = ALIGN_CENTER
        c_no.font = FONT_ROW
        c_no.border = BORDER_DATA
        if row_fill:
            c_no.fill = row_fill

        # Tahun
        c_yr = ws1.cell(row=curr_row, column=2, value=row["tahun"])
        c_yr.alignment = ALIGN_CENTER
        c_yr.font = FONT_ROW_BOLD
        c_yr.border = BORDER_DATA
        if row_fill:
            c_yr.fill = row_fill

        # Pillars
        for p_idx, p_name in enumerate(sorted_pillars):
            p_val = row["pillars"].get(p_name, 0)
            c_p = ws1.cell(row=curr_row, column=3 + p_idx, value=p_val)
            c_p.alignment = ALIGN_RIGHT
            c_p.font = FONT_ROW
            c_p.number_format = NUM_FMT_CURRENCY
            c_p.border = BORDER_DATA
            if row_fill:
                c_p.fill = row_fill

        # Total Realisasi
        tot_col = 3 + len(sorted_pillars)
        total_val = sum(row["pillars"].values())
        c_tot = ws1.cell(row=curr_row, column=tot_col, value=total_val)
        c_tot.alignment = ALIGN_RIGHT
        c_tot.font = FONT_ROW_BOLD
        c_tot.number_format = NUM_FMT_CURRENCY
        c_tot.border = BORDER_DATA
        if row_fill:
            c_tot.fill = row_fill

        curr_row += 1

    # Total Summary Row for Sheet 1
    if yearly_data:
        ws1.row_dimensions[curr_row].height = 22
        ws1.cell(row=curr_row, column=1, value="")
        c_lbl = ws1.cell(row=curr_row, column=2, value="TOTAL")
        c_lbl.font = FONT_ROW_BOLD
        c_lbl.alignment = ALIGN_CENTER
        c_lbl.fill = FILL_TOTAL
        c_lbl.border = BORDER_TOTAL

        first_data_row = start_row + 1
        last_data_row = curr_row - 1

        for col_idx in range(3, 3 + len(sorted_pillars) + 1):
            col_letter = get_column_letter(col_idx)
            c_sum = ws1.cell(row=curr_row, column=col_idx)
            c_sum.value = f"=SUM({col_letter}{first_data_row}:{col_letter}{last_data_row})"
            c_sum.font = FONT_ROW_BOLD
            c_sum.alignment = ALIGN_RIGHT
            c_sum.fill = FILL_TOTAL
            c_sum.border = BORDER_TOTAL
            c_sum.number_format = NUM_FMT_CURRENCY

    # Auto-adjust column widths
    for col in ws1.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            # Skip title rows in measuring
            if cell.row < start_row:
                continue
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws1.column_dimensions[col_letter].width = max(max_len + 4, 12)
    ws1.column_dimensions["A"].width = 8
    ws1.column_dimensions["B"].width = 12

    # -------------------------------------------------------------
    # 2. SHEET 2: Detail Transaksi (Drill-Through)
    # -------------------------------------------------------------
    ws2 = wb.create_sheet("Detail Transaksi")
    ws2.views.sheetView[0].showGridLines = True

    trx_rows = get_dashboard_trend_transactions(
        company_id,
        years=years,
        pillars=pillars,
        programs=programs,
        jenjangs=jenjangs,
        statuses=statuses,
        angkatans=angkatans,
    )

    # Title block
    ws2["A1"] = "DETAIL TRANSAKSI REALISASI BEASISWA (DRILL-THROUGH)"
    ws2["A1"].font = FONT_MAIN_TITLE
    ws2["A2"] = f"Eka Tjipta Foundation (ETF) — Total: {len(trx_rows):,} Transaksi"
    ws2["A2"].font = FONT_SUBTITLE
    ws2["A3"] = f"Filter: {'; '.join(filter_desc) if filter_desc else 'Semua Data'}"
    ws2["A3"].font = FONT_META
    ws2["A4"] = f"Tanggal Unduh: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    ws2["A4"].font = FONT_META

    headers2 = [
        "No",
        "Tahun",
        "Tanggal Payment",
        "Kode Siswa",
        "Nama Mahasiswa",
        "Universitas",
        "Pillar",
        "Program",
        "Jenjang",
        "Angkatan",
        "Kategori (Cat 1)",
        "Kategori 2 (Cat 2)",
        "No PAM",
        "Perusahaan",
        "Status",
        "Amount (Rp)",
    ]

    ws2.row_dimensions[start_row].height = 24
    for col_idx, h in enumerate(headers2, 1):
        cell = ws2.cell(row=start_row, column=col_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER_DATA

    curr_row = start_row + 1
    for no, r in enumerate(trx_rows, 1):
        ws2.row_dimensions[curr_row].height = 19
        is_alt = (no % 2 == 0)
        row_fill = FILL_ROW_ALT if is_alt else None

        row_vals = [
            (no, ALIGN_CENTER, FONT_ROW, None),
            (r.get("tahun") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("tanggal") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("siswa_code") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("nama") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("universitas") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("pillar") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("program") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("jenjang") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("angkatan") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("cat1") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("cat2") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("pam") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("perusahaan") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("status") or "", ALIGN_CENTER, FONT_ROW, None),
            (float(r.get("amount") or 0), ALIGN_RIGHT, FONT_ROW_BOLD, NUM_FMT_CURRENCY),
        ]

        for col_idx, (val, align, font, num_fmt) in enumerate(row_vals, 1):
            cell = ws2.cell(row=curr_row, column=col_idx, value=val)
            cell.alignment = align
            cell.font = font
            cell.border = BORDER_DATA
            if num_fmt:
                cell.number_format = num_fmt
            if row_fill:
                cell.fill = row_fill

        curr_row += 1

    # Total Summary Row for Sheet 2
    if trx_rows:
        ws2.row_dimensions[curr_row].height = 22
        for col_idx in range(1, 16):
            c_empty = ws2.cell(row=curr_row, column=col_idx, value="")
            c_empty.fill = FILL_TOTAL
            c_empty.border = BORDER_TOTAL

        ws2.cell(row=curr_row, column=15, value="TOTAL").alignment = ALIGN_RIGHT
        ws2.cell(row=curr_row, column=15).font = FONT_ROW_BOLD
        ws2.cell(row=curr_row, column=15).fill = FILL_TOTAL
        ws2.cell(row=curr_row, column=15).border = BORDER_TOTAL

        amt_col_letter = get_column_letter(16)
        first_trx_row = start_row + 1
        last_trx_row = curr_row - 1
        c_amt_total = ws2.cell(row=curr_row, column=16)
        c_amt_total.value = f"=SUM({amt_col_letter}{first_trx_row}:{amt_col_letter}{last_trx_row})"
        c_amt_total.font = FONT_ROW_BOLD
        c_amt_total.alignment = ALIGN_RIGHT
        c_amt_total.fill = FILL_TOTAL
        c_amt_total.border = BORDER_TOTAL
        c_amt_total.number_format = NUM_FMT_CURRENCY

        # Enable auto filter on Sheet 2
        last_row_filter = curr_row - 1
        ws2.auto_filter.ref = f"A{start_row}:P{last_row_filter}"

    # Auto-adjust column widths for Sheet 2
    col_min_widths = {
        "A": 8,   # No
        "B": 10,  # Tahun
        "C": 14,  # Tanggal
        "D": 14,  # Kode Siswa
        "E": 26,  # Nama
        "F": 26,  # Universitas
        "G": 12,  # Pillar
        "H": 18,  # Program
        "I": 10,  # Jenjang
        "J": 10,  # Angkatan
        "K": 18,  # Cat 1
        "L": 18,  # Cat 2
        "M": 22,  # No PAM
        "N": 20,  # Perusahaan
        "O": 12,  # Status
        "P": 18,  # Amount
    }
    for col_letter, width in col_min_widths.items():
        ws2.column_dimensions[col_letter].width = width

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def export_payment_excel(
    company_id: int,
    search: str = "",
    cat1: str = "",
    pillar: str = "",
    bulan: str = "",
    tahun: str = "",
    status: str = "",
    program: str = "",
) -> bytes:
    from modules.beasiswa.service import get_payment_list

    data = get_payment_list(
        company_id,
        search=search,
        cat1=cat1,
        pillar=pillar,
        bulan=bulan,
        tahun=tahun,
        status=status,
        program=program,
        limit=100000,
    )
    rows = data.get("rows", [])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Payment"
    ws.views.sheetView[0].showGridLines = True

    # Title Block
    ws["A1"] = "DAFTAR TRANSAKSI PAYMENT BEASISWA"
    ws["A1"].font = FONT_MAIN_TITLE
    ws["A2"] = f"Eka Tjipta Foundation (ETF) — Total: {len(rows):,} Records"
    ws["A2"].font = FONT_SUBTITLE

    filters_applied = []
    if search:
        filters_applied.append(f"Cari: {search}")
    if cat1:
        filters_applied.append(f"Kategori 1: {cat1}")
    if pillar:
        filters_applied.append(f"Pillar: {pillar}")
    if bulan:
        filters_applied.append(f"Bulan: {bulan}")
    if tahun:
        filters_applied.append(f"Tahun: {tahun}")
    if program:
        filters_applied.append(f"Program: {program}")
    if status:
        filters_applied.append(f"Status: {status}")

    ws["A3"] = f"Filter: {'; '.join(filters_applied) if filters_applied else 'Semua Data'}"
    ws["A3"].font = FONT_META
    ws["A4"] = f"Tanggal Unduh: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    ws["A4"].font = FONT_META

    headers = [
        "No",
        "Kode",
        "Nama Siswa",
        "Program",
        "Kategori 1",
        "Kategori 2",
        "Tanggal",
        "Pillar",
        "Amount (Rp)",
        "PAM",
        "Tgl Bayar PAM",
        "Perusahaan",
        "Status",
    ]

    start_row = 6
    ws.row_dimensions[start_row].height = 24

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=col_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER_DATA

    curr_row = start_row + 1
    for no, r in enumerate(rows, 1):
        ws.row_dimensions[curr_row].height = 19
        is_alt = (no % 2 == 0)
        row_fill = FILL_ROW_ALT if is_alt else None

        row_vals = [
            (no, ALIGN_CENTER, FONT_ROW, None),
            (r.get("siswa_code") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("nama") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("program") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("cat1") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("cat2") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("tanggal") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("pillar") or "", ALIGN_CENTER, FONT_ROW, None),
            (float(r.get("amount") or 0), ALIGN_RIGHT, FONT_ROW_BOLD, NUM_FMT_CURRENCY),
            (r.get("pam") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("tgl_bayar_pam") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("perusahaan") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("status") or "", ALIGN_CENTER, FONT_ROW, None),
        ]

        for col_idx, (val, align, font, num_fmt) in enumerate(row_vals, 1):
            cell = ws.cell(row=curr_row, column=col_idx, value=val)
            cell.alignment = align
            cell.font = font
            cell.border = BORDER_DATA
            if num_fmt:
                cell.number_format = num_fmt
            if row_fill:
                cell.fill = row_fill

        curr_row += 1

    # Total Summary Row
    if rows:
        ws.row_dimensions[curr_row].height = 22
        for col_idx in range(1, 9):
            c_empty = ws.cell(row=curr_row, column=col_idx, value="")
            c_empty.fill = FILL_TOTAL
            c_empty.border = BORDER_TOTAL

        ws.cell(row=curr_row, column=8, value="TOTAL").alignment = ALIGN_RIGHT
        ws.cell(row=curr_row, column=8).font = FONT_ROW_BOLD
        ws.cell(row=curr_row, column=8).fill = FILL_TOTAL
        ws.cell(row=curr_row, column=8).border = BORDER_TOTAL

        amt_col_letter = get_column_letter(9)
        first_row = start_row + 1
        last_row = curr_row - 1
        c_amt_total = ws.cell(row=curr_row, column=9)
        c_amt_total.value = f"=SUM({amt_col_letter}{first_row}:{amt_col_letter}{last_row})"
        c_amt_total.font = FONT_ROW_BOLD
        c_amt_total.alignment = ALIGN_RIGHT
        c_amt_total.fill = FILL_TOTAL
        c_amt_total.border = BORDER_TOTAL
        c_amt_total.number_format = NUM_FMT_CURRENCY

        for col_idx in range(10, len(headers) + 1):
            c_tail = ws.cell(row=curr_row, column=col_idx, value="")
            c_tail.fill = FILL_TOTAL
            c_tail.border = BORDER_TOTAL

        # Auto filter
        ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(headers))}{curr_row - 1}"

    # Auto-adjust column widths
    col_min_widths = {
        "A": 8,   # No
        "B": 14,  # Kode
        "C": 26,  # Nama Siswa
        "D": 18,  # Program
        "E": 18,  # Kategori 1
        "F": 18,  # Kategori 2
        "G": 14,  # Tanggal
        "H": 12,  # Pillar
        "I": 18,  # Amount
        "J": 22,  # PAM
        "K": 16,  # Tgl Bayar PAM
        "L": 22,  # Perusahaan
        "M": 12,  # Status
    }
    for col_letter, width in col_min_widths.items():
        ws.column_dimensions[col_letter].width = width

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
