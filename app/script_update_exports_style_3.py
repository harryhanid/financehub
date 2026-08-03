path = r"C:\Financehub\app\modules\sponsorship\exports.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

import re

pattern = re.compile(r"# --- Styles ---.*(?=def export_data_excel)", re.DOTALL)

new_code = """# --- Styles ---
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
_COLUMN_LABELS = ["NO", "LEMBAGA / PERORANGAN", "PERIHAL", "APP", "AGRI", "ENERGY & FINANCE", "PROPERTY", "TOTAL"]

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
            elif col == 6: cell.fill = AGRI_FILL
            elif col == 7: cell.fill = EF_FILL
            elif col == 8: cell.fill = PROP_FILL

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
                r["app_amount"], r["agri_amount"], r["energy_finance_amount"], r["property_amount"], r["total"]
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
            sub["app_amount"], sub["agri_amount"], sub["energy_finance_amount"], sub["property_amount"], sub["total"]
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
        gt["app_amount"], gt["agri_amount"], gt["energy_finance_amount"], gt["property_amount"], gt["total"]
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
        f"{pct['app_amount']}%", f"{pct['agri_amount']}%", f"{pct['energy_finance_amount']}%", f"{pct['property_amount']}%", ""
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
    ws.column_dimensions["G"].width = 43  # ~300 pixels
    ws.column_dimensions["H"].width = 20
    ws.column_dimensions["I"].width = 20

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

"""

new_content = pattern.sub(new_code, c)

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("done")
