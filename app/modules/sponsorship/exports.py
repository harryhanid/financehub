import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from modules.sponsorship.service import get_sponsorship_report, PILLAR_COLUMNS

# --- Styles ---
ARIAL_11 = Font(name='Arial', size=11)
ARIAL_11_BOLD = Font(name='Arial', size=11, bold=True)
ARIAL_11_WHITE_BOLD = Font(name='Arial', size=11, bold=True, color="FFFFFF")

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
        right=THIN_GRAY if col == 9 else None
    )

_NUM_FMT = '#,##0;-#,##0;"-"'
_COLUMN_LABELS = ["NO", "LEMBAGA / PERORANGAN", "PERIHAL", "APP", "ENERGY", "PROPERTY", "AGRI", "TOTAL"]

def export_report_excel(company_id: int, tahun: str, cat4_mode: str) -> bytes:
    data = get_sponsorship_report(company_id, tahun, cat4_mode)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"

    # Title row
    ws.append(["", f"RANGKUMAN SPONSORSHIP - in Rp Full Amount"])
    ws["B1"].font = ARIAL_11_BOLD
    ws.merge_cells(start_row=1, start_column=2, end_row=1, end_column=9)
    ws.append([])

    def _write_section_headers():
        # Dark Blue Header Row
        ws.append(["", f"RANGKUMAN SPONSORSHIP {data['tahun']} - in Rp Full Amount"])
        row = ws.max_row
        ws.row_dimensions[row].height = 19.8
        for col in range(2, 10):
            cell = ws.cell(row=row, column=col)
            cell.fill = DARK_BLUE_FILL
            cell.font = ARIAL_11_WHITE_BOLD
            cell.border = get_border(col)
            cell.alignment = Alignment(vertical="center")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=9)

        # Column Labels Row
        ws.append([""] + _COLUMN_LABELS)
        row = ws.max_row
        ws.row_dimensions[row].height = 54
        for col in range(2, 10):
            cell = ws.cell(row=row, column=col)
            cell.font = ARIAL_11_BOLD
            cell.alignment = ALIGN_CENTER
            cell.border = get_border(col)
            
            # Map columns to colors: 2=NO, 3=LEMBAGA, 4=PERIHAL, 5=APP, 6=AGRI, 7=EF, 8=PROP, 9=TOTAL
            if col in [2, 3, 4, 9]:
                cell.fill = DARK_BLUE_FILL
                cell.font = ARIAL_11_WHITE_BOLD
            elif col == 5: cell.fill = APP_FILL
            elif col == 6: cell.fill = EF_FILL
            elif col == 7: cell.fill = PROP_FILL
            elif col == 8: cell.fill = AGRI_FILL

    if not data["sections"]:
        _write_section_headers()
        
    # Sort sections from largest total amount to smallest
    data["sections"].sort(key=lambda s: s["subtotal"]["total"], reverse=True)

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
        for col in range(2, 10):
            cell = ws.cell(row=row, column=col)
            cell.fill = YELLOW_FILL
            cell.font = ARIAL_11_BOLD
            cell.border = get_border(col)
            cell.alignment = Alignment(vertical="center")
        # ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=9) # Not merged, matching earlier

        # Data Rows
        for r in section["rows"]:
            ws.append(["", 
                r["no"], r["lembaga_perorangan"], r["perihal"] or "",
                r["app_amount"], r["energy_finance_amount"], r["property_amount"], r["agri_amount"], r["total"]
            ])
            row = ws.max_row
            
            # Auto-fit row height approximation
            text_len = len(r["perihal"] or "")
            # Base height is 34.5 points (46px). Add 15 points (20px) per extra 50 chars.
            extra_lines = max(0, (text_len - 45) // 45)
            row_height = 34.5 + (extra_lines * 15.0)
            ws.row_dimensions[row].height = row_height
            
            for col in range(2, 10):
                cell = ws.cell(row=row, column=col)
                cell.font = ARIAL_11
                cell.border = get_border(col)
                cell.alignment = Alignment(vertical="center")
                if col >= 5:
                    cell.number_format = _NUM_FMT
                    cell.alignment = ALIGN_RIGHT
            
            ws.cell(row=row, column=2).alignment = ALIGN_CENTER
            ws.cell(row=row, column=3).alignment = ALIGN_WRAP
            ws.cell(row=row, column=4).alignment = ALIGN_WRAP

        # Subtotal Row
        sub = section["subtotal"]
        ws.append(["", 
            f"TOTAL {section['description'].upper()}", "", "",
            sub["app_amount"], sub["energy_finance_amount"], sub["property_amount"], sub["agri_amount"], sub["total"]
        ])
        row = ws.max_row
        ws.row_dimensions[row].height = 19.8
        for col in range(2, 10):
            cell = ws.cell(row=row, column=col)
            cell.fill = YELLOW_FILL
            cell.font = ARIAL_11_BOLD
            cell.border = get_border(col)
            cell.alignment = Alignment(vertical="center")
            if col >= 5:
                cell.number_format = _NUM_FMT
                cell.alignment = ALIGN_RIGHT

    # Grand Total
    gt = data["grand_total"]
    ws.append(["", 
        "TOTAL SPONSORSHIP (ACTUAL)", "", "",
        gt["app_amount"], gt["energy_finance_amount"], gt["property_amount"], gt["agri_amount"], gt["total"]
    ])
    row = ws.max_row
    ws.row_dimensions[row].height = 19.8
    for col in range(2, 10):
        cell = ws.cell(row=row, column=col)
        cell.fill = DARK_BLUE_FILL
        cell.font = ARIAL_11_WHITE_BOLD
        cell.border = get_border(col)
        cell.alignment = Alignment(vertical="center")
        if col >= 5:
            cell.number_format = _NUM_FMT
            cell.alignment = ALIGN_RIGHT

    # PCT Allocation
    pct = data["pct_allocation"]
    ws.append(["", 
        "% Allocation", "", "",
        f"{pct['app_amount']}%", f"{pct['energy_finance_amount']}%", f"{pct['property_amount']}%", f"{pct['agri_amount']}%", ""
    ])
    row = ws.max_row
    ws.row_dimensions[row].height = 19.8
    for col in range(2, 10):
        cell = ws.cell(row=row, column=col)
        cell.font = ARIAL_11_BOLD
        cell.border = get_border(col)
        cell.alignment = Alignment(vertical="center")
        if col >= 5:
            cell.alignment = ALIGN_RIGHT

    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 5
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 50
    ws.column_dimensions["E"].width = 20
    ws.column_dimensions["F"].width = 20
    ws.column_dimensions["G"].width = 22.08  # ~300 pixels
    ws.column_dimensions["H"].width = 20
    ws.column_dimensions["I"].width = 20

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
    from modules.sponsorship.service import get_sponsorship_outstanding
    sections, grand_total = get_sponsorship_outstanding(company_id, filters)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Outstanding Sponsorship"
    
    headers = ["Kategori", "Tanggal", "Lembaga/Perorangan", "Amount Request", "Status"]
    ws.append(headers)
    
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
    
    for section in sections:
        ws.append([section["cat2_label"]])
        row_idx = ws.max_row
        ws.cell(row=row_idx, column=1).font = _SECTION_FONT
        ws.cell(row=row_idx, column=1).fill = _SECTION_FILL
        
        for r in section["rows"]:
            ws.append(["", r.get("tanggal_form_sponsor"), r.get("lembaga_perorangan"), r.get("amount_request"), r.get("status")])
            
        ws.append(["", "", "Subtotal", section["subtotal"], ""])
        row_idx = ws.max_row
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=row_idx, column=col)
            cell.font = _SECTION_FONT
            cell.fill = _SECTION_FILL
            
    ws.append(["", "", "Grand Total", grand_total, ""])
    row_idx = ws.max_row
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=row_idx, column=col)
        cell.font = _GRANDTOTAL_FONT
        cell.fill = _GRANDTOTAL_FILL
    
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
