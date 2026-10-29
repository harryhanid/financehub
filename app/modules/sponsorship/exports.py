import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from modules.sponsorship.service import get_sponsorship_report, PILLAR_COLUMNS

# --- Styles ---
ARIAL_11 = Font(name='Arial', size=11)
ARIAL_11_BOLD = Font(name='Arial', size=11, bold=True)
ARIAL_11_WHITE_BOLD = Font(name='Arial', size=11, bold=True, color="FFFFFF")
PCT_FONT = Font(name='Arial', size=11, bold=True, italic=True, color="CC0066")  # % Allocation row
PCT_FILL = PatternFill("solid", fgColor="D9D9D9")        # RGB 217,217,217

DARK_BLUE_FILL = PatternFill("solid", fgColor="16365C")  # Navy
YELLOW_FILL = PatternFill("solid", fgColor="FFFF00")     # Yellow
APP_FILL = PatternFill("solid", fgColor="F2DCDB")        # APP
AGRI_FILL = PatternFill("solid", fgColor="F79646")       # AGRI
EF_FILL = PatternFill("solid", fgColor="9BBB59")         # E&F
PROP_FILL = PatternFill("solid", fgColor="B1A0C7")       # PROPERTY

ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")
ALIGN_WRAP = Alignment(wrap_text=True, vertical="center")

THIN_GRAY = Side(style='thin', color='A6A6A6')

def get_border(col):
    return Border(
        top=THIN_GRAY,
        bottom=THIN_GRAY,
        left=THIN_GRAY if col == 2 else None,
        right=THIN_GRAY if col == 11 else None
    )

_NUM_FMT = '#,##0;-#,##0;"-"'
_COLUMN_LABELS = ["NO", "TANGGAL PAYMENT", "REFF", "LEMBAGA / PERORANGAN", "PERIHAL", "APP", "ENERGY", "PROPERTY", "AGRI", "TOTAL"]

def export_report_excel(company_id: int, tahun: str, cat4_mode: str, bulan=None) -> bytes:
    data = get_sponsorship_report(company_id, tahun, cat4_mode, bulan)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"

    # Title row
    ws.append(["", f"RANGKUMAN SPONSORSHIP - in Rp Full Amount"])
    ws["B1"].font = ARIAL_11_BOLD
    ws.merge_cells(start_row=1, start_column=2, end_row=1, end_column=11)
    ws.append([])

    def _write_section_headers():
        # Dark Blue Header Row
        ws.append(["", f"RANGKUMAN SPONSORSHIP {data['tahun']} - in Rp Full Amount"])
        row = ws.max_row
        ws.row_dimensions[row].height = 19.8
        for col in range(2, 12):
            cell = ws.cell(row=row, column=col)
            cell.fill = DARK_BLUE_FILL
            cell.font = ARIAL_11_WHITE_BOLD
            cell.border = get_border(col)
            cell.alignment = Alignment(vertical="center")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=11)

        # Column Labels Row
        ws.append([""] + _COLUMN_LABELS)
        row = ws.max_row
        ws.row_dimensions[row].height = 54
        for col in range(2, 12):
            cell = ws.cell(row=row, column=col)
            cell.font = ARIAL_11_BOLD
            cell.alignment = ALIGN_CENTER
            cell.border = get_border(col)
            
            # Map columns to colors: 2=NO, 3=TGL, 4=REFF, 5=LEMBAGA, 6=PERIHAL, 7=APP, 8=EF, 9=PROP, 10=AGRI, 11=TOTAL
            if col in [2, 3, 4, 5, 6, 11]:
                cell.fill = DARK_BLUE_FILL
                cell.font = ARIAL_11_WHITE_BOLD
            elif col == 7: cell.fill = APP_FILL
            elif col == 8: cell.fill = EF_FILL
            elif col == 9: cell.fill = PROP_FILL
            elif col == 10: cell.fill = AGRI_FILL

    if not data["sections"]:
        _write_section_headers()
        
    # Sort sections from largest total amount to smallest
    # (Removed to respect config.SPONSORSHIP_DESCRIPTION order)
    # data["sections"].sort(key=lambda s: s["subtotal"]["total"], reverse=True)

    for section in data["sections"]:
        _write_section_headers()
        
        # Sort rows within section by total amount descending
        section["rows"].sort(key=lambda r: r.get("total", 0), reverse=True)
        # Update numbering
        for i, r in enumerate(section["rows"], start=1):
            r["no"] = i
        
        # Category Row (Yellow)
        ws.append(["", section["description"].upper()])
        row = ws.max_row
        ws.row_dimensions[row].height = 19.8
        for col in range(2, 12):
            cell = ws.cell(row=row, column=col)
            cell.fill = YELLOW_FILL
            cell.font = ARIAL_11_BOLD
            cell.border = get_border(col)
            cell.alignment = Alignment(vertical="center")
        # ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=11) # Not merged, matching earlier

        # Data Rows
        for r in section["rows"]:
            ws.append(["", 
                r["no"], r.get("tanggal_payment", ""), str(r.get("reff", "")), r["lembaga_perorangan"], r["perihal"] or "",
                r["app_amount"], r["energy_finance_amount"], r["property_amount"], r["agri_amount"], r["total"]
            ])
            row = ws.max_row
            
            # Auto-fit row height approximation
            text_len = len(r["perihal"] or "")
            # Base height is 34.5 points (46px). Add 15 points (20px) per extra 50 chars.
            extra_lines = max(0, (text_len - 45) // 45)
            row_height = 34.5 + (extra_lines * 15.0)
            ws.row_dimensions[row].height = row_height
            
            for col in range(2, 12):
                cell = ws.cell(row=row, column=col)
                cell.font = ARIAL_11
                cell.border = get_border(col)
                cell.alignment = Alignment(vertical="center")
                if col >= 7:
                    cell.number_format = _NUM_FMT
                    cell.alignment = ALIGN_RIGHT
            
            ws.cell(row=row, column=2).alignment = ALIGN_CENTER
            ws.cell(row=row, column=3).alignment = ALIGN_WRAP
            ws.cell(row=row, column=4).alignment = ALIGN_WRAP
            ws.cell(row=row, column=5).alignment = ALIGN_WRAP
            ws.cell(row=row, column=6).alignment = ALIGN_WRAP

        # Subtotal Row
        sub = section["subtotal"]
        ws.append(["", 
            f"TOTAL {section['description'].upper()}", "", "", "", "",
            sub["app_amount"], sub["energy_finance_amount"], sub["property_amount"], sub["agri_amount"], sub["total"]
        ])
        row = ws.max_row
        ws.row_dimensions[row].height = 19.8
        for col in range(2, 12):
            cell = ws.cell(row=row, column=col)
            cell.fill = YELLOW_FILL
            cell.font = ARIAL_11_BOLD
            cell.border = get_border(col)
            cell.alignment = Alignment(vertical="center")
            if col >= 7:
                cell.number_format = _NUM_FMT
                cell.alignment = ALIGN_RIGHT

    # Grand Total
    gt = data["grand_total"]
    ws.append(["", 
        "TOTAL SPONSORSHIP (ACTUAL)", "", "", "", "",
        gt["app_amount"], gt["energy_finance_amount"], gt["property_amount"], gt["agri_amount"], gt["total"]
    ])
    row = ws.max_row
    ws.row_dimensions[row].height = 19.8
    for col in range(2, 12):
        cell = ws.cell(row=row, column=col)
        cell.fill = DARK_BLUE_FILL
        cell.font = ARIAL_11_WHITE_BOLD
        cell.border = get_border(col)
        cell.alignment = Alignment(vertical="center")
        if col >= 7:
            cell.number_format = _NUM_FMT
            cell.alignment = ALIGN_RIGHT

    # PCT Allocation
    pct = data["pct_allocation"]
    ws.append(["", 
        "", "", "", "", "% Allocation",
        f"{pct['app_amount']}%", f"{pct['energy_finance_amount']}%", f"{pct['property_amount']}%", f"{pct['agri_amount']}%", ""
    ])
    row = ws.max_row
    ws.row_dimensions[row].height = 19.8
    for col in range(2, 12):
        cell = ws.cell(row=row, column=col)
        cell.font = PCT_FONT
        cell.fill = PCT_FILL
        cell.border = get_border(col)
        cell.alignment = ALIGN_RIGHT

    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 5
    ws.column_dimensions["C"].width = 15   # TANGGAL PAYMENT
    ws.column_dimensions["D"].width = 15   # REFF
    ws.column_dimensions["E"].width = 40   # LEMBAGA
    ws.column_dimensions["F"].width = 50   # PERIHAL
    ws.column_dimensions["G"].width = 20   # APP
    ws.column_dimensions["H"].width = 20   # ENERGY
    ws.column_dimensions["I"].width = 22.08 # PROPERTY
    ws.column_dimensions["J"].width = 20   # AGRI
    ws.column_dimensions["K"].width = 20   # TOTAL

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

_HEADER_FILL = PatternFill("solid", fgColor="E0E0E0")
_HEADER_FONT = Font(bold=True)

def export_data_excel(company_id: int, filters: dict) -> bytes:
    from modules.sponsorship.service import list_transaksi
    rows = list_transaksi(company_id, filters)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Sponsorship"
    
    headers = [
        "ID", "Cat", "Description", "Tanggal Form", "Tanggal Payment",
        "Cat1", "Cat2", "Cat3", "Lembaga / Perorangan", "Perihal",
        "Amount Request", "APP", "ENERGY", "PROPERTY", "AGRI",
        "Reff", "Status", "Cat4", "COA", "CC Total", "CC", "Source"
    ]
    ws.append(headers)
    
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
    
    for r in rows:
        row_data = [
            r.get("id"), r.get("cat"), r.get("description"), r.get("tanggal_form_sponsor"), r.get("tanggal_payment"),
            r.get("cat1"), r.get("cat2"), r.get("cat3"), r.get("lembaga_perorangan"), r.get("perihal"),
            r.get("amount_request"), r.get("app"), r.get("energy_finance"), r.get("property"), r.get("agri"),
            r.get("reff"), r.get("status"), r.get("cat4"), r.get("coa"), r.get("cc_total"), r.get("cc"), r.get("source")
        ]
        ws.append(row_data)
        
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_outstanding_excel(company_id: int, filters: dict) -> bytes:
    from modules.sponsorship.service import get_sponsorship_outstanding, list_proposals
    sections, grand_total = get_sponsorship_outstanding(company_id, filters)
    
    prop_filters = {"status": "Open"}
    if filters.get("tahun"):
        prop_filters["tahun"] = filters.get("tahun")
    open_proposals = list_proposals(company_id, prop_filters, limit=2000, offset=0)
    open_total = sum(float(p.get("total_amount") or 0) for p in open_proposals)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Outstanding Sponsorship"
    
    # Enable grid lines
    ws.views.sheetView[0].showGridLines = True
    
    # Styles matching outstanding.html
    hdr_fill = PatternFill("solid", fgColor="1E3A8A")
    grand_fill = PatternFill("solid", fgColor="256D7B")
    sec_fill = PatternFill("solid", fgColor="5B929E")
    zebra_fill = PatternFill("solid", fgColor="F8FAFC")
    
    font_hdr = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    font_bold_white = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    font_regular = Font(name="Arial", size=10)
    
    thin_side = Side(style="thin", color="D1D5DB")
    cell_border = Border(top=thin_side, bottom=thin_side, left=thin_side, right=thin_side)
    
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    
    headers = [
        "NO",
        "Tanggal Approval",
        "Reff",
        "LEMBAGA/ PERORANGAN",
        "PERIHAL",
        "Amount in Rp",
        "Status Sponsor"
    ]
    num_cols = len(headers)
    
    # Header row
    ws.append(headers)
    ws.row_dimensions[1].height = 24
    for col_idx in range(1, num_cols + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = hdr_fill
        cell.font = font_hdr
        cell.border = cell_border
        if col_idx in [1, 2, 3, 7]:
            cell.alignment = align_center
        elif col_idx in [4, 5]:
            cell.alignment = align_left
        elif col_idx == 6:
            cell.alignment = align_right

    # Grand Total row (matching outstanding.html top row)
    ws.append(["Total Outstanding Sponsorship", "", "", "", "", grand_total, ""])
    gt_row = ws.max_row
    ws.row_dimensions[gt_row].height = 22
    ws.merge_cells(start_row=gt_row, start_column=1, end_row=gt_row, end_column=5)
    for col_idx in range(1, num_cols + 1):
        cell = ws.cell(row=gt_row, column=col_idx)
        cell.fill = grand_fill
        cell.font = font_bold_white
        cell.border = cell_border
        if col_idx == 1:
            cell.alignment = align_left
        elif col_idx == 6:
            cell.alignment = align_right
            cell.number_format = _NUM_FMT
        elif col_idx == 7:
            cell.alignment = align_center

    # Section rows
    for section in sections:
        # Category Header row
        ws.append([section["cat2_label"], "", "", "", "", section["subtotal"], ""])
        sec_row = ws.max_row
        ws.row_dimensions[sec_row].height = 20
        ws.merge_cells(start_row=sec_row, start_column=1, end_row=sec_row, end_column=5)
        for col_idx in range(1, num_cols + 1):
            cell = ws.cell(row=sec_row, column=col_idx)
            cell.fill = sec_fill
            cell.font = font_bold_white
            cell.border = cell_border
            if col_idx == 1:
                cell.alignment = align_left
            elif col_idx == 6:
                cell.alignment = align_right
                cell.number_format = _NUM_FMT
            elif col_idx == 7:
                cell.alignment = align_center

        # Item rows
        for idx, r in enumerate(section["rows"]):
            ws.append([
                r.get("no"),
                r.get("tanggal_approval") or "",
                r.get("reff") or "",
                r.get("lembaga_perorangan") or "",
                r.get("perihal") or "",
                r.get("amount") or 0.0,
                r.get("status") or ""
            ])
            r_idx = ws.max_row
            ws.row_dimensions[r_idx].height = 19
            is_even = (idx % 2 == 1)
            row_fill = zebra_fill if is_even else None
            
            for col_idx in range(1, num_cols + 1):
                cell = ws.cell(row=r_idx, column=col_idx)
                cell.font = font_regular
                cell.border = cell_border
                if row_fill:
                    cell.fill = row_fill
                if col_idx in [1, 2, 3, 7]:
                    cell.alignment = align_center
                elif col_idx in [4, 5]:
                    cell.alignment = align_left
                elif col_idx == 6:
                    cell.alignment = align_right
                    cell.number_format = _NUM_FMT

    if open_proposals:
        prop_sec_fill = PatternFill("solid", fgColor="0D9488")
        ws.append([f"Proposal Sponsor (Status: Open) - {len(open_proposals)} Proposal", "", "", "", "", open_total, ""])
        prop_row = ws.max_row
        ws.row_dimensions[prop_row].height = 20
        ws.merge_cells(start_row=prop_row, start_column=1, end_row=prop_row, end_column=5)
        for col_idx in range(1, num_cols + 1):
            cell = ws.cell(row=prop_row, column=col_idx)
            cell.fill = prop_sec_fill
            cell.font = font_bold_white
            cell.border = cell_border
            if col_idx == 1:
                cell.alignment = align_left
            elif col_idx == 6:
                cell.alignment = align_right
                cell.number_format = _NUM_FMT
            elif col_idx == 7:
                cell.alignment = align_center

        months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        for idx, p in enumerate(open_proposals, start=1):
            tgl_raw = str(p.get("tanggal") or "")
            tgl_display = tgl_raw
            if len(tgl_raw) >= 7 and "-" in tgl_raw:
                try:
                    parts = tgl_raw.split("-")
                    m_idx = int(parts[1]) - 1
                    if 0 <= m_idx < 12:
                        tgl_display = f"{months[m_idx]} {parts[0]}"
                except Exception:
                    pass

            ws.append([
                idx,
                tgl_display,
                p.get("referensi") or "",
                "",
                p.get("kegiatan") or "",
                float(p.get("total_amount") or 0.0),
                ""
            ])
            r_idx = ws.max_row
            ws.row_dimensions[r_idx].height = 19
            is_even = (idx % 2 == 1)
            row_fill = zebra_fill if is_even else None
            
            for col_idx in range(1, num_cols + 1):
                cell = ws.cell(row=r_idx, column=col_idx)
                cell.font = font_regular
                cell.border = cell_border
                if row_fill:
                    cell.fill = row_fill
                if col_idx in [1, 2, 3, 7]:
                    cell.alignment = align_center
                elif col_idx in [4, 5]:
                    cell.alignment = align_left
                elif col_idx == 6:
                    cell.alignment = align_right
                    cell.number_format = _NUM_FMT

        # Overall Grand Total row
        overall_fill = PatternFill("solid", fgColor="1E293B")
        ws.append(["Total Keseluruhan (Outstanding + Proposal Open)", "", "", "", "", grand_total + open_total, ""])
        tot_row = ws.max_row
        ws.row_dimensions[tot_row].height = 22
        ws.merge_cells(start_row=tot_row, start_column=1, end_row=tot_row, end_column=5)
        for col_idx in range(1, num_cols + 1):
            cell = ws.cell(row=tot_row, column=col_idx)
            cell.fill = overall_fill
            cell.font = font_bold_white
            cell.border = cell_border
            if col_idx == 1:
                cell.alignment = align_left
            elif col_idx == 6:
                cell.alignment = align_right
                cell.number_format = _NUM_FMT
            elif col_idx == 7:
                cell.alignment = align_center

    # Freeze header + grand total row
    ws.freeze_panes = "A3"

    # Column widths
    ws.column_dimensions["A"].width = 7    # NO
    ws.column_dimensions["B"].width = 18   # Tanggal Approval
    ws.column_dimensions["C"].width = 16   # Reff
    ws.column_dimensions["D"].width = 38   # LEMBAGA/ PERORANGAN
    ws.column_dimensions["E"].width = 44   # PERIHAL
    ws.column_dimensions["F"].width = 22   # Amount in Rp
    ws.column_dimensions["G"].width = 18   # Status Sponsor

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_MR_HEADERS = [
    "Account Management", "ID#", "Date", "Allocation Memo", "Budget Activity",
    "COST CENTER", "DEBIT - CREDIT", "Source", "COA HO", "COST CENTER2",
    "Month", "CC0", "CC1", "BC1", "New Code", "Memo", "BC",
]
_MR_ROW_KEYS = [
    "account_management", "id_no", "date", "allocation_memo", "budget_activity",
    "cost_center", "debit_credit", "source", "coa_ho", "cost_center2",
    "month", "cc0", "cc1", "bc1", "new_code", "memo", "bc",
]
_MR_RED_FILL = PatternFill("solid", fgColor="C00000")
_MR_DATE_FMT = "dd-mmm-yy"
_MR_NUM_FMT = '#,##0;-#,##0;"-"'
_MR_COL_WIDTHS = [16, 8, 12, 55, 14, 12, 16, 10, 12, 14, 8, 6, 6, 8, 14, 60, 22]


def export_mr_excel(company_id: int, tahun: list) -> bytes:
    from modules.sponsorship.service import get_sponsorship_mr
    rows = get_sponsorship_mr(company_id, tahun)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "MR"

    ws.append(_MR_HEADERS)
    for col in range(1, len(_MR_HEADERS) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = ARIAL_11_WHITE_BOLD
        cell.alignment = ALIGN_CENTER
        cell.fill = _MR_RED_FILL if 9 <= col <= 14 else DARK_BLUE_FILL

    for r in rows:
        ws.append([r[key] for key in _MR_ROW_KEYS])
        row_idx = ws.max_row
        for col, key in enumerate(_MR_ROW_KEYS, start=1):
            cell = ws.cell(row=row_idx, column=col)
            cell.font = ARIAL_11
            if key == "date":
                cell.number_format = _MR_DATE_FMT
            elif key in ("account_management", "coa_ho", "debit_credit"):
                cell.number_format = _MR_NUM_FMT
                cell.alignment = ALIGN_RIGHT

    for i, w in enumerate(_MR_COL_WIDTHS, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# --- Sponsorship Proposal & Form Exports ---

def terbilang_id(n: int | float) -> str:
    """Konversi angka nominal ke kalimat terbilang Bahasa Indonesia."""
    try:
        n = int(round(float(n or 0)))
    except (ValueError, TypeError):
        return "Nol"
    if n == 0:
        return "Nol"
    if n < 0:
        return "Minus " + terbilang_id(abs(n))

    satuan = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
    if n < 12:
        return satuan[n]
    elif n < 20:
        return terbilang_id(n - 10) + " Belas"
    elif n < 100:
        return terbilang_id(n // 10) + " Puluh" + (" " + terbilang_id(n % 10) if n % 10 != 0 else "")
    elif n < 200:
        return "Seratus" + (" " + terbilang_id(n - 100) if n - 100 != 0 else "")
    elif n < 1000:
        return terbilang_id(n // 100) + " Ratus" + (" " + terbilang_id(n % 100) if n % 100 != 0 else "")
    elif n < 2000:
        return "Seribu" + (" " + terbilang_id(n - 1000) if n - 1000 != 0 else "")
    elif n < 1000000:
        return terbilang_id(n // 1000) + " Ribu" + (" " + terbilang_id(n % 1000) if n % 1000 != 0 else "")
    elif n < 1000000000:
        return terbilang_id(n // 1000000) + " Juta" + (" " + terbilang_id(n % 1000000) if n % 1000000 != 0 else "")
    elif n < 1000000000000:
        return terbilang_id(n // 1000000000) + " Miliar" + (" " + terbilang_id(n % 1000000000) if n % 1000000000 != 0 else "")
    else:
        return terbilang_id(n // 1000000000000) + " Triliun" + (" " + terbilang_id(n % 1000000000000) if n % 1000000000000 != 0 else "")


def format_terbilang(amount: float) -> str:
    if not amount or amount <= 0:
        return "-"
    return f"#  {terbilang_id(amount)} Rupiah #"


def format_terbilang_pillar(amount: float) -> str:
    if not amount or amount <= 0:
        return ""
    return f"( {terbilang_id(amount)} Rupiah )"


def format_tanggal_indo(tgl_raw: str) -> str:
    """Mengubah format YYYY-MM-DD atau ISO string menjadi 'DD MMMM YYYY' bahasa Indonesia.
    Contoh: '2026-09-28' -> '28 September 2026'."""
    if not tgl_raw:
        return ""
    tgl_clean = str(tgl_raw).split("T")[0].split(" ")[0].strip()
    parts = tgl_clean.split("-")
    if len(parts) == 3 and len(parts[0]) == 4:
        months_indo = [
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]
        try:
            year = parts[0]
            month_idx = int(parts[1]) - 1
            day = int(parts[2])
            if 0 <= month_idx < 12:
                return f"{day} {months_indo[month_idx]} {year}"
        except Exception:
            pass
    return tgl_clean


def export_proposal_form_excel(proposal: dict) -> bytes:
    """Mengisi template Form.xlsx dengan data proposal sponsor dan mengembalikan bytes xlsx."""
    import io
    import os
    import openpyxl

    template_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "storage", "templates", "Form_Sponsorship_Template.xlsx"),
        "C:/Financehub/app/storage/templates/Form_Sponsorship_Template.xlsx",
        "C:/Users/25010160/Downloads/Form Sponsor/Form.xlsx",
    ]
    template_file = None
    for p in template_paths:
        if os.path.exists(p):
            template_file = p
            break

    if not template_file:
        raise FileNotFoundError("Template Form_Sponsorship_Template.xlsx tidak ditemukan di storage.")

    wb = openpyxl.load_workbook(template_file)
    ws = wb["Form Sponsorship Propose New"] if "Form Sponsorship Propose New" in wb.sheetnames else wb.active

    # Data Utama
    ws["G3"].value = format_tanggal_indo(proposal.get("tanggal") or "")
    ws["G4"].value = proposal.get("referensi") or ""
    ws["G5"].value = proposal.get("kegiatan") or ""
    
    tot_amt = float(proposal.get("total_amount") or 0)
    ws["H6"].value = tot_amt
    ws["G7"].value = format_terbilang(tot_amt)
    ws["G8"].value = proposal.get("catatan") or "Nilai Sumbangan diatas netto excluded/ diluar pajak PPN/PPh"

    # Enforce pillar labels
    ws["E11"].value = "APP"
    ws["E14"].value = "AGRO"

    # 1. APP
    app_amt = float(proposal.get("app_amount") or 0)
    ws["C11"].value = "√" if app_amt > 0 else "X"
    ws["I10"].value = "Rp." if app_amt > 0 else "-"
    ws["J10"].value = app_amt if app_amt > 0 else ""
    ws["K10"].value = format_terbilang_pillar(app_amt)

    # 2. AGRO (AGRI)
    agri_amt = float(proposal.get("agri_amount") or 0)
    ws["C14"].value = "√" if agri_amt > 0 else "X"
    ws["I13"].value = "Rp." if agri_amt > 0 else "-"
    ws["J13"].value = agri_amt if agri_amt > 0 else ""
    ws["K13"].value = format_terbilang_pillar(agri_amt)

    # 3. ENERGY
    energy_amt = float(proposal.get("energy_amount") or 0)
    ws["C17"].value = "√" if energy_amt > 0 else "X"
    ws["I16"].value = "Rp." if energy_amt > 0 else "-"
    ws["J16"].value = energy_amt if energy_amt > 0 else ""
    ws["K16"].value = format_terbilang_pillar(energy_amt)

    # 4. LAND
    land_amt = float(proposal.get("land_amount") or 0)
    ws["C20"].value = "√" if land_amt > 0 else "X"
    ws["I19"].value = "Rp." if land_amt > 0 else "-"
    ws["J19"].value = land_amt if land_amt > 0 else ""
    ws["K19"].value = format_terbilang_pillar(land_amt)

    # 5. FINANCE
    fin_amt = float(proposal.get("finance_amount") or 0)
    ws["C23"].value = "√" if fin_amt > 0 else "X"
    ws["I22"].value = "Rp." if fin_amt > 0 else "-"
    ws["J22"].value = fin_amt if fin_amt > 0 else ""
    ws["K22"].value = format_terbilang_pillar(fin_amt)

    # Signatures
    ws["B34"].value = proposal.get("diajukan_oleh") or "AR/JT"
    ws["I34"].value = "FS"
    ws["L34"].value = "SC"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_proposals_bulk_zip(proposals: list) -> bytes:
    """Mengekspor daftar proposal ke dalam file ZIP berisi file Excel individual Form Sponsorship."""
    import io
    import zipfile

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in proposals:
            no_prop = (p.get("nomor_proposal") or f"PROP_{p.get('id', 0)}").replace("/", "_").replace("\\", "_")
            xls_bytes = export_proposal_form_excel(p)
            filename = f"Sponsorship_Form_{no_prop}.xlsx"
            zf.writestr(filename, xls_bytes)

    return zip_buf.getvalue()


def export_proposals_master_excel(company_id: int, filters: dict) -> bytes:
    """Mengekspor seluruh data proposal sponsor ke dalam format Excel master (sesuai struktur Database.xlsx)."""
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from modules.sponsorship.service import list_proposals

    rows = list_proposals(company_id, filters, limit=10000, offset=0)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    headers = [
        "ID", "Tanggal", "Referensi", "Kegiatan",
        "APP", "AGRI", "ENERGY", "LAND", "FINANCE", "TOTAL",
        "Diajukan Oleh", "Versi", "Status", "Approval Date"
    ]
    ws.append(headers)

    header_fill = PatternFill("solid", fgColor="16365C")  # Navy
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Arial", size=10)
    num_fmt = '#,##0;-#,##0;"-"'

    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in rows:
        row_data = [
            r.get("nomor_proposal"),
            r.get("tanggal"),
            r.get("referensi"),
            r.get("kegiatan"),
            float(r.get("app_amount") or 0),
            float(r.get("agri_amount") or 0),
            float(r.get("energy_amount") or 0),
            float(r.get("land_amount") or 0),
            float(r.get("finance_amount") or 0),
            float(r.get("total_amount") or 0),
            r.get("diajukan_oleh") or "AR/JT",
            r.get("versi") or "",
            r.get("status") or "Open",
            r.get("approval_date") or ""
        ]
        ws.append(row_data)
        row_idx = ws.max_row
        for col_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            if 5 <= col_idx <= 10:
                cell.number_format = num_fmt
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif col_idx in (1, 2, 11, 12, 13, 14):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    col_widths = {
        'A': 18, 'B': 14, 'C': 28, 'D': 45,
        'E': 16, 'F': 16, 'G': 16, 'H': 16, 'I': 16, 'J': 18,
        'K': 14, 'L': 12, 'M': 12, 'N': 16
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

