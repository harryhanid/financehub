# modules/beasiswa/exports.py
import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from database import get_conn
from modules.beasiswa.service import (
    get_dashboard_pillar_yearly,
    get_dashboard_trend_transactions,
    get_dashboard_breakdown,
    get_dashboard_monthly,
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

NUM_FMT_CURRENCY = '#,##0;(#,##0);"-'
NUM_FMT_PERCENT = '0.0%'

BULAN_NAMES = [
    "",
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
]


def _build_drill_through_detail_sheet(wb, trx_rows, filter_desc, title_suffix=""):
    ws2 = wb.create_sheet("Detail Transaksi")
    ws2.views.sheetView[0].showGridLines = True

    # Title block
    ws2["A1"] = f"DETAIL TRANSAKSI REALISASI BEASISWA{title_suffix} (DRILL-THROUGH)"
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

    start_row = 6
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

    return ws2


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
    known_order = ["AGRI", "APP", "EFIN", "PROPERTY", "SETF"]
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
    trx_rows = get_dashboard_trend_transactions(
        company_id,
        years=years,
        pillars=pillars,
        programs=programs,
        jenjangs=jenjangs,
        statuses=statuses,
        angkatans=angkatans,
    )
    _build_drill_through_detail_sheet(wb, trx_rows, filter_desc)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def export_dashboard_kategori_excel(
    company_id: int,
    cat1: str = None,
    years: list = None,
    pillars: list = None,
    programs: list = None,
    jenjangs: list = None,
    statuses: list = None,
    angkatans: list = None,
) -> bytes:
    wb = openpyxl.Workbook()

    # 1. SHEET 1: Realisasi per Kategori
    ws1 = wb.active
    ws1.title = "Realisasi per Kategori"
    ws1.views.sheetView[0].showGridLines = True

    breakdown_data = get_dashboard_breakdown(
        company_id,
        years=years,
        pillars=pillars,
        programs=programs,
        jenjangs=jenjangs,
        statuses=statuses,
        angkatans=angkatans,
    )
    kategori_data = breakdown_data.get("kategori", [])
    if cat1:
        kategori_data = [k for k in kategori_data if k.get("cat1") == cat1]

    # Sort standard categories first
    known_cats = ["By Pendidikan", "By Tunjangan", "By Penelitian", "By Medical"]
    kategori_data = sorted(
        kategori_data,
        key=lambda k: (known_cats.index(k["cat1"]) if k.get("cat1") in known_cats else 99, k.get("cat1") or "")
    )

    # Title block
    ws1["A1"] = "REALISASI BEASISWA PER KATEGORI" + (f" - {cat1.upper()}" if cat1 else "")
    ws1["A1"].font = FONT_MAIN_TITLE
    ws1["A2"] = "Eka Tjipta Foundation (ETF)"
    ws1["A2"].font = FONT_SUBTITLE

    filter_desc = []
    if cat1:
        filter_desc.append(f"Kategori: {cat1}")
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

    headers1 = ["No", "Kategori", "Budget (Rp)", "Realisasi (Rp)", "Sisa Budget (Rp)", "% Realisasi"]
    start_row = 6
    ws1.row_dimensions[start_row].height = 24

    for col_idx, h in enumerate(headers1, 1):
        cell = ws1.cell(row=start_row, column=col_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER_DATA

    curr_row = start_row + 1
    for no, row in enumerate(kategori_data, 1):
        ws1.row_dimensions[curr_row].height = 20
        is_alt = (no % 2 == 0)
        row_fill = FILL_ROW_ALT if is_alt else None

        # No
        c_no = ws1.cell(row=curr_row, column=1, value=no)
        c_no.alignment = ALIGN_CENTER
        c_no.font = FONT_ROW
        c_no.border = BORDER_DATA
        if row_fill: c_no.fill = row_fill

        # Kategori
        c_cat = ws1.cell(row=curr_row, column=2, value=row.get("cat1") or "(Tanpa Kategori)")
        c_cat.alignment = ALIGN_LEFT
        c_cat.font = FONT_ROW_BOLD
        c_cat.border = BORDER_DATA
        if row_fill: c_cat.fill = row_fill

        # Budget
        c_bgt = ws1.cell(row=curr_row, column=3, value=float(row.get("budget") or 0))
        c_bgt.alignment = ALIGN_RIGHT
        c_bgt.font = FONT_ROW
        c_bgt.number_format = NUM_FMT_CURRENCY
        c_bgt.border = BORDER_DATA
        if row_fill: c_bgt.fill = row_fill

        # Realisasi
        c_rea = ws1.cell(row=curr_row, column=4, value=float(row.get("realisasi") or 0))
        c_rea.alignment = ALIGN_RIGHT
        c_rea.font = FONT_ROW
        c_rea.number_format = NUM_FMT_CURRENCY
        c_rea.border = BORDER_DATA
        if row_fill: c_rea.fill = row_fill

        # Sisa Budget: =C{curr_row}-D{curr_row}
        c_sisa = ws1.cell(row=curr_row, column=5, value=f"=C{curr_row}-D{curr_row}")
        c_sisa.alignment = ALIGN_RIGHT
        c_sisa.font = FONT_ROW_BOLD
        c_sisa.number_format = NUM_FMT_CURRENCY
        c_sisa.border = BORDER_DATA
        if row_fill: c_sisa.fill = row_fill

        # % Realisasi: =IF(C{curr_row}>0, D{curr_row}/C{curr_row}, 0)
        c_pct = ws1.cell(row=curr_row, column=6, value=f"=IF(C{curr_row}>0, D{curr_row}/C{curr_row}, 0)")
        c_pct.alignment = ALIGN_RIGHT
        c_pct.font = FONT_ROW_BOLD
        c_pct.number_format = NUM_FMT_PERCENT
        c_pct.border = BORDER_DATA
        if row_fill: c_pct.fill = row_fill

        curr_row += 1

    # Total Summary Row for Sheet 1
    if kategori_data:
        ws1.row_dimensions[curr_row].height = 22
        ws1.cell(row=curr_row, column=1, value="")
        c_lbl = ws1.cell(row=curr_row, column=2, value="TOTAL")
        c_lbl.font = FONT_ROW_BOLD
        c_lbl.alignment = ALIGN_CENTER
        c_lbl.fill = FILL_TOTAL
        c_lbl.border = BORDER_TOTAL

        first_data_row = start_row + 1
        last_data_row = curr_row - 1

        # Budget Total
        c_tot_bgt = ws1.cell(row=curr_row, column=3, value=f"=SUM(C{first_data_row}:C{last_data_row})")
        c_tot_bgt.font = FONT_ROW_BOLD
        c_tot_bgt.alignment = ALIGN_RIGHT
        c_tot_bgt.fill = FILL_TOTAL
        c_tot_bgt.border = BORDER_TOTAL
        c_tot_bgt.number_format = NUM_FMT_CURRENCY

        # Realisasi Total
        c_tot_rea = ws1.cell(row=curr_row, column=4, value=f"=SUM(D{first_data_row}:D{last_data_row})")
        c_tot_rea.font = FONT_ROW_BOLD
        c_tot_rea.alignment = ALIGN_RIGHT
        c_tot_rea.fill = FILL_TOTAL
        c_tot_rea.border = BORDER_TOTAL
        c_tot_rea.number_format = NUM_FMT_CURRENCY

        # Sisa Total
        c_tot_sisa = ws1.cell(row=curr_row, column=5, value=f"=SUM(E{first_data_row}:E{last_data_row})")
        c_tot_sisa.font = FONT_ROW_BOLD
        c_tot_sisa.alignment = ALIGN_RIGHT
        c_tot_sisa.fill = FILL_TOTAL
        c_tot_sisa.border = BORDER_TOTAL
        c_tot_sisa.number_format = NUM_FMT_CURRENCY

        # % Realisasi Total
        c_tot_pct = ws1.cell(row=curr_row, column=6, value=f"=IF(C{curr_row}>0, D{curr_row}/C{curr_row}, 0)")
        c_tot_pct.font = FONT_ROW_BOLD
        c_tot_pct.alignment = ALIGN_RIGHT
        c_tot_pct.fill = FILL_TOTAL
        c_tot_pct.border = BORDER_TOTAL
        c_tot_pct.number_format = NUM_FMT_PERCENT

    # Auto-adjust column widths
    ws1.column_dimensions["A"].width = 8
    ws1.column_dimensions["B"].width = 24
    ws1.column_dimensions["C"].width = 20
    ws1.column_dimensions["D"].width = 20
    ws1.column_dimensions["E"].width = 20
    ws1.column_dimensions["F"].width = 16

    # 2. SHEET 2: Detail Transaksi
    trx_rows = get_dashboard_trend_transactions(
        company_id,
        years=years,
        pillars=pillars,
        programs=programs,
        jenjangs=jenjangs,
        statuses=statuses,
        angkatans=angkatans,
        cat1=cat1,
    )
    title_suffix = f" - {cat1.upper()}" if cat1 else ""
    _build_drill_through_detail_sheet(wb, trx_rows, filter_desc, title_suffix=title_suffix)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def export_dashboard_bulanan_excel(
    company_id: int,
    bulan: int = None,
    years: list = None,
    pillars: list = None,
    programs: list = None,
    jenjangs: list = None,
    statuses: list = None,
    angkatans: list = None,
) -> bytes:
    wb = openpyxl.Workbook()

    # If years not provided, fetch all distinct years in database
    if not years:
        conn = get_conn()
        y_rows = conn.execute(
            "SELECT DISTINCT fh_strftime('%Y', tanggal) AS y FROM payment_beasiswa WHERE company_id = ? AND tanggal IS NOT NULL AND tanggal != '' ORDER BY y ASC NULLS FIRST",
            (company_id,),
        ).fetchall()
        conn.close()
        years = [int(r["y"]) for r in y_rows if r["y"] and str(r["y"]).isdigit()]

    if not years:
        current_year = datetime.now().year
        years = [current_year - 1, current_year]

    years = sorted(list(set(years)))

    # 1. SHEET 1: Trend Realisasi Bulanan
    ws1 = wb.active
    ws1.title = "Trend per Bulan"
    ws1.views.sheetView[0].showGridLines = True

    monthly_data = get_dashboard_monthly(
        company_id,
        years=years,
        pillars=pillars,
        programs=programs,
        jenjangs=jenjangs,
        statuses=statuses,
        angkatans=angkatans,
    )
    comparison = monthly_data.get("comparison", [])
    if bulan and 1 <= bulan <= 12:
        comparison = [row for row in comparison if row.get("bulan") == bulan]

    # Title block
    ws1["A1"] = "TREND REALISASI BEASISWA PER BULAN" + (f" - {BULAN_NAMES[bulan].upper()}" if (bulan and 1 <= bulan <= 12) else "")
    ws1["A1"].font = FONT_MAIN_TITLE
    ws1["A2"] = "Eka Tjipta Foundation (ETF)"
    ws1["A2"].font = FONT_SUBTITLE

    filter_desc = []
    if bulan and 1 <= bulan <= 12:
        filter_desc.append(f"Bulan: {BULAN_NAMES[bulan]}")
    if years:
        filter_desc.append(f"Tahun: {', '.join(str(y) for y in years)}")
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

    headers1 = ["No", "Bulan"] + [str(y) for y in years] + ["Total Realisasi (Rp)"]
    start_row = 6
    ws1.row_dimensions[start_row].height = 24

    for col_idx, h in enumerate(headers1, 1):
        cell = ws1.cell(row=start_row, column=col_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER_DATA

    curr_row = start_row + 1
    for no, row in enumerate(comparison, 1):
        ws1.row_dimensions[curr_row].height = 20
        is_alt = (no % 2 == 0)
        row_fill = FILL_ROW_ALT if is_alt else None

        b_num = row.get("bulan", 1)
        b_name = BULAN_NAMES[b_num] if (1 <= b_num <= 12) else f"Bulan {b_num}"

        # No
        c_no = ws1.cell(row=curr_row, column=1, value=no)
        c_no.alignment = ALIGN_CENTER
        c_no.font = FONT_ROW
        c_no.border = BORDER_DATA
        if row_fill: c_no.fill = row_fill

        # Bulan
        c_bln = ws1.cell(row=curr_row, column=2, value=b_name)
        c_bln.alignment = ALIGN_LEFT
        c_bln.font = FONT_ROW_BOLD
        c_bln.border = BORDER_DATA
        if row_fill: c_bln.fill = row_fill

        # Years
        for y_idx, y in enumerate(years):
            val = float(row.get("per_tahun", {}).get(str(y)) or 0)
            c_y = ws1.cell(row=curr_row, column=3 + y_idx, value=val)
            c_y.alignment = ALIGN_RIGHT
            c_y.font = FONT_ROW
            c_y.number_format = NUM_FMT_CURRENCY
            c_y.border = BORDER_DATA
            if row_fill: c_y.fill = row_fill

        # Total Realisasi
        tot_col = 3 + len(years)
        first_y_letter = get_column_letter(3)
        last_y_letter = get_column_letter(2 + len(years))
        c_tot = ws1.cell(row=curr_row, column=tot_col, value=f"=SUM({first_y_letter}{curr_row}:{last_y_letter}{curr_row})")
        c_tot.alignment = ALIGN_RIGHT
        c_tot.font = FONT_ROW_BOLD
        c_tot.number_format = NUM_FMT_CURRENCY
        c_tot.border = BORDER_DATA
        if row_fill: c_tot.fill = row_fill

        curr_row += 1

    # Total Summary Row for Sheet 1
    if comparison:
        ws1.row_dimensions[curr_row].height = 22
        ws1.cell(row=curr_row, column=1, value="")
        c_lbl = ws1.cell(row=curr_row, column=2, value="TOTAL")
        c_lbl.font = FONT_ROW_BOLD
        c_lbl.alignment = ALIGN_CENTER
        c_lbl.fill = FILL_TOTAL
        c_lbl.border = BORDER_TOTAL

        first_data_row = start_row + 1
        last_data_row = curr_row - 1

        for col_idx in range(3, 3 + len(years) + 1):
            col_letter = get_column_letter(col_idx)
            c_sum = ws1.cell(row=curr_row, column=col_idx)
            c_sum.value = f"=SUM({col_letter}{first_data_row}:{col_letter}{last_data_row})"
            c_sum.font = FONT_ROW_BOLD
            c_sum.alignment = ALIGN_RIGHT
            c_sum.fill = FILL_TOTAL
            c_sum.border = BORDER_TOTAL
            c_sum.number_format = NUM_FMT_CURRENCY

    # Column widths
    ws1.column_dimensions["A"].width = 8
    ws1.column_dimensions["B"].width = 16
    for col_idx in range(3, 3 + len(years) + 1):
        col_letter = get_column_letter(col_idx)
        ws1.column_dimensions[col_letter].width = 18

    # 2. SHEET 2: Detail Transaksi
    trx_rows = get_dashboard_trend_transactions(
        company_id,
        years=years,
        pillars=pillars,
        programs=programs,
        jenjangs=jenjangs,
        statuses=statuses,
        angkatans=angkatans,
        bulan=bulan,
    )
    title_suffix = f" - BULAN {BULAN_NAMES[bulan].upper()}" if (bulan and 1 <= bulan <= 12) else ""
    _build_drill_through_detail_sheet(wb, trx_rows, filter_desc, title_suffix=title_suffix)

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


def export_budget_excel(
    company_id: int,
    search: str = "",
    cat1: str = "",
    pillar: str = "",
    bulan: str = "",
    tahun: str = "",
    program: str = "",
) -> bytes:
    from modules.beasiswa.service import get_budget_list

    data = get_budget_list(
        company_id,
        search=search,
        cat1=cat1,
        pillar=pillar,
        bulan=bulan,
        tahun=tahun,
        program=program,
        limit=100000,
    )
    rows = data.get("rows", [])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Budget"
    ws.views.sheetView[0].showGridLines = True

    # Title Block
    ws["A1"] = "DAFTAR BUDGET BEASISWA"
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
        "Tgl Expired",
        "Pillar",
        "Amount (Rp)",
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
            (r.get("tgl_expired") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("pillar") or "", ALIGN_CENTER, FONT_ROW, None),
            (float(r.get("amount") or 0), ALIGN_RIGHT, FONT_ROW_BOLD, NUM_FMT_CURRENCY),
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
        for col_idx in range(1, 10):
            c_empty = ws.cell(row=curr_row, column=col_idx, value="")
            c_empty.fill = FILL_TOTAL
            c_empty.border = BORDER_TOTAL

        ws.cell(row=curr_row, column=9, value="TOTAL").alignment = ALIGN_RIGHT
        ws.cell(row=curr_row, column=9).font = FONT_ROW_BOLD
        ws.cell(row=curr_row, column=9).fill = FILL_TOTAL
        ws.cell(row=curr_row, column=9).border = BORDER_TOTAL

        amt_col_letter = get_column_letter(10)
        first_row = start_row + 1
        last_row = curr_row - 1
        c_amt_total = ws.cell(row=curr_row, column=10)
        c_amt_total.value = f"=SUM({amt_col_letter}{first_row}:{amt_col_letter}{last_row})"
        c_amt_total.font = FONT_ROW_BOLD
        c_amt_total.alignment = ALIGN_RIGHT
        c_amt_total.fill = FILL_TOTAL
        c_amt_total.border = BORDER_TOTAL
        c_amt_total.number_format = NUM_FMT_CURRENCY

        # Auto filter
        ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(headers))}{curr_row - 1}"

    col_min_widths = {
        "A": 8,   # No
        "B": 14,  # Kode
        "C": 26,  # Nama Siswa
        "D": 18,  # Program
        "E": 18,  # Kategori 1
        "F": 18,  # Kategori 2
        "G": 14,  # Tanggal
        "H": 14,  # Tgl Expired
        "I": 12,  # Pillar
        "J": 18,  # Amount
    }
    for col_letter, width in col_min_widths.items():
        ws.column_dimensions[col_letter].width = width

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def export_rekap_excel(
    company_id: int,
    search: str = "",
    program: str = "",
    pillar: str = "",
    jenjang: str = "",
    angkatan: str = "",
    status: str = "",
) -> bytes:
    from modules.beasiswa.service import get_rekap

    rows = get_rekap(
        company_id,
        program=program,
        pillar=pillar,
        status=status,
        search=search,
        jenjang=jenjang,
        angkatan=angkatan,
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Siswa"
    ws.views.sheetView[0].showGridLines = True

    # Title Block
    ws["A1"] = "DAFTAR DATA SISWA BEASISWA"
    ws["A1"].font = FONT_MAIN_TITLE
    ws["A2"] = f"Eka Tjipta Foundation (ETF) — Total: {len(rows):,} Siswa"
    ws["A2"].font = FONT_SUBTITLE

    filters_applied = []
    if search:
        filters_applied.append(f"Cari: {search}")
    if program:
        filters_applied.append(f"Program: {program}")
    if pillar:
        filters_applied.append(f"Pillar: {pillar}")
    if jenjang:
        filters_applied.append(f"Jenjang: {jenjang}")
    if angkatan:
        filters_applied.append(f"Angkatan: {angkatan}")
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
        "Jenjang",
        "Angkatan",
        "Program",
        "Status",
        "Total Budget (Rp)",
        "Total Payment (Rp)",
        "Sisa (Rp)",
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
            (r.get("code") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("nama") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("jenjang") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("angkatan") or "", ALIGN_CENTER, FONT_ROW, None),
            (r.get("program") or "", ALIGN_LEFT, FONT_ROW, None),
            (r.get("status") or "", ALIGN_CENTER, FONT_ROW, None),
            (float(r.get("total_budget") or 0), ALIGN_RIGHT, FONT_ROW, NUM_FMT_CURRENCY),
            (float(r.get("total_payment") or 0), ALIGN_RIGHT, FONT_ROW, NUM_FMT_CURRENCY),
            (float(r.get("sisa") or 0), ALIGN_RIGHT, FONT_ROW_BOLD, NUM_FMT_CURRENCY),
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
        for col_idx in range(1, 8):
            c_empty = ws.cell(row=curr_row, column=col_idx, value="")
            c_empty.fill = FILL_TOTAL
            c_empty.border = BORDER_TOTAL

        ws.cell(row=curr_row, column=7, value="TOTAL").alignment = ALIGN_RIGHT
        ws.cell(row=curr_row, column=7).font = FONT_ROW_BOLD
        ws.cell(row=curr_row, column=7).fill = FILL_TOTAL
        ws.cell(row=curr_row, column=7).border = BORDER_TOTAL

        first_row = start_row + 1
        last_row = curr_row - 1
        for col_idx in (8, 9, 10):
            col_letter = get_column_letter(col_idx)
            c_sum = ws.cell(row=curr_row, column=col_idx)
            c_sum.value = f"=SUM({col_letter}{first_row}:{col_letter}{last_row})"
            c_sum.font = FONT_ROW_BOLD
            c_sum.alignment = ALIGN_RIGHT
            c_sum.fill = FILL_TOTAL
            c_sum.border = BORDER_TOTAL
            c_sum.number_format = NUM_FMT_CURRENCY

        # Auto filter
        ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(headers))}{curr_row - 1}"

    col_min_widths = {
        "A": 8,   # No
        "B": 14,  # Kode
        "C": 26,  # Nama Siswa
        "D": 12,  # Jenjang
        "E": 12,  # Angkatan
        "F": 20,  # Program
        "G": 12,  # Status
        "H": 18,  # Total Budget
        "I": 18,  # Total Payment
        "J": 18,  # Sisa
    }
    for col_letter, width in col_min_widths.items():
        ws.column_dimensions[col_letter].width = width

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
