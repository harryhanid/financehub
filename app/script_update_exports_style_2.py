path = r"C:\Financehub\app\modules\sponsorship\exports.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

import re

# We will replace the styling and export_report_excel
pattern = re.compile(r"# --- Styles ---.*(?=def export_data_excel)", re.DOTALL)

new_styles_and_func = """# --- Styles ---
ARIAL_11 = Font(name='Arial', size=11)
ARIAL_11_BOLD = Font(name='Arial', size=11, bold=True)
ARIAL_11_WHITE_BOLD = Font(name='Arial', size=11, bold=True, color="FFFFFF")

DARK_BLUE_FILL = PatternFill("solid", fgColor="11325B")  # Dark blue for headers
YELLOW_FILL = PatternFill("solid", fgColor="FFFF00")     # Yellow for categories/subtotals
APP_FILL = PatternFill("solid", fgColor="FCE4D6")        # Light peach/pink
AGRI_FILL = PatternFill("solid", fgColor="F4B183")       # Light orange
EF_FILL = PatternFill("solid", fgColor="A9D08E")         # Light green
PROP_FILL = PatternFill("solid", fgColor="B4A7D6")       # Light purple

ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")
ALIGN_WRAP = Alignment(wrap_text=True, vertical="center")

# Border only top and bottom, color #A6A6A6
TOP_BOTTOM_BORDER = Border(
    top=Side(style='thin', color='A6A6A6'),
    bottom=Side(style='thin', color='A6A6A6')
)

_NUM_FMT = '#,##0;-#,##0;"-"'
_COLUMN_LABELS = ["NO", "LEMBAGA / PERORANGAN", "PERIHAL", "APP", "AGRI", "ENERGY & FINANCE", "PROPERTY", "TOTAL"]

def export_report_excel(company_id: int, tahun: str, cat4_mode: str) -> bytes:
    data = get_sponsorship_report(company_id, tahun, cat4_mode)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"

    # Title row
    ws.append([f"RANGKUMAN SPONSORSHIP - in Rp Full Amount"])
    ws["A1"].font = ARIAL_11_BOLD
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)
    ws.append([])

    def _write_section_headers():
        # Dark Blue Header Row
        ws.append([f"RANGKUMAN SPONSORSHIP {data['tahun']} - in Rp Full Amount"])
        row = ws.max_row
        ws.row_dimensions[row].height = 19.8  # Will set 19.8 points
        for col in range(1, 9):
            cell = ws.cell(row=row, column=col)
            cell.fill = DARK_BLUE_FILL
            cell.font = ARIAL_11_WHITE_BOLD
            cell.border = TOP_BOTTOM_BORDER
            cell.alignment = Alignment(vertical="center")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)

        # Column Labels Row
        ws.append(_COLUMN_LABELS)
        row = ws.max_row
        ws.row_dimensions[row].height = 54  # 72 pixels
        for col in range(1, 9):
            cell = ws.cell(row=row, column=col)
            cell.font = ARIAL_11_BOLD
            cell.alignment = ALIGN_CENTER
            cell.border = TOP_BOTTOM_BORDER
            
            if col in [1, 2, 3, 8]:
                cell.fill = DARK_BLUE_FILL
                cell.font = ARIAL_11_WHITE_BOLD
            elif col == 4: cell.fill = APP_FILL
            elif col == 5: cell.fill = AGRI_FILL
            elif col == 6: cell.fill = EF_FILL
            elif col == 7: cell.fill = PROP_FILL

    if not data["sections"]:
        _write_section_headers()

    for section in data["sections"]:
        _write_section_headers()
        
        # Sort rows by total amount descending
        section["rows"].sort(key=lambda r: r.get("total", 0), reverse=True)
        # Update numbering after sort
        for i, r in enumerate(section["rows"], start=1):
            r["no"] = i
        
        # Category Row (Yellow)
        ws.append([section["description"].upper()])
        row = ws.max_row
        ws.row_dimensions[row].height = 19.8
        for col in range(1, 9):
            cell = ws.cell(row=row, column=col)
            cell.fill = YELLOW_FILL
            cell.font = ARIAL_11_BOLD
            cell.border = TOP_BOTTOM_BORDER
            cell.alignment = Alignment(vertical="center")

        # Data Rows
        for r in section["rows"]:
            ws.append([
                r["no"], r["lembaga_perorangan"], r["perihal"] or "",
                r["app_amount"], r["agri_amount"], r["energy_finance_amount"], r["property_amount"], r["total"]
            ])
            row = ws.max_row
            ws.row_dimensions[row].height = 34.5  # 46 pixels
            for col in range(1, 9):
                cell = ws.cell(row=row, column=col)
                cell.font = ARIAL_11
                cell.border = TOP_BOTTOM_BORDER
                cell.alignment = Alignment(vertical="center")
                if col >= 4:
                    cell.number_format = _NUM_FMT
                    cell.alignment = ALIGN_RIGHT
            
            ws.cell(row=row, column=1).alignment = ALIGN_CENTER
            ws.cell(row=row, column=2).alignment = ALIGN_WRAP
            ws.cell(row=row, column=3).alignment = ALIGN_WRAP

        # Subtotal Row
        sub = section["subtotal"]
        ws.append([
            f"TOTAL {section['description'].upper()}", "", "",
            sub["app_amount"], sub["agri_amount"], sub["energy_finance_amount"], sub["property_amount"], sub["total"]
        ])
        row = ws.max_row
        ws.row_dimensions[row].height = 19.8
        for col in range(1, 9):
            cell = ws.cell(row=row, column=col)
            cell.fill = YELLOW_FILL
            cell.font = ARIAL_11_BOLD
            cell.border = TOP_BOTTOM_BORDER
            cell.alignment = Alignment(vertical="center")
            if col >= 4:
                cell.number_format = _NUM_FMT
                cell.alignment = ALIGN_RIGHT

    # Grand Total
    gt = data["grand_total"]
    ws.append([
        "TOTAL SPONSORSHIP (ACTUAL)", "", "",
        gt["app_amount"], gt["agri_amount"], gt["energy_finance_amount"], gt["property_amount"], gt["total"]
    ])
    row = ws.max_row
    ws.row_dimensions[row].height = 19.8
    for col in range(1, 9):
        cell = ws.cell(row=row, column=col)
        cell.fill = DARK_BLUE_FILL
        cell.font = ARIAL_11_WHITE_BOLD
        cell.border = TOP_BOTTOM_BORDER
        cell.alignment = Alignment(vertical="center")
        if col >= 4:
            cell.number_format = _NUM_FMT
            cell.alignment = ALIGN_RIGHT

    # PCT Allocation
    pct = data["pct_allocation"]
    ws.append([
        "% Allocation", "", "",
        f"{pct['app_amount']}%", f"{pct['agri_amount']}%", f"{pct['energy_finance_amount']}%", f"{pct['property_amount']}%", ""
    ])
    row = ws.max_row
    ws.row_dimensions[row].height = 19.8
    for col in range(1, 9):
        cell = ws.cell(row=row, column=col)
        cell.font = ARIAL_11_BOLD
        cell.border = TOP_BOTTOM_BORDER
        cell.alignment = Alignment(vertical="center")
        if col >= 4:
            cell.alignment = ALIGN_RIGHT

    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 50
    for col_letter in ("D", "E", "F", "G", "H"):
        ws.column_dimensions[col_letter].width = 20

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

"""

new_content = pattern.sub(new_styles_and_func, c)

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("done")
