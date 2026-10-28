import os

exports_path = r'C:\Financehub\app\modules\sponsorship\exports.py'
with open(exports_path, 'r', encoding='utf-8') as f:
    exports_content = f.read()

# Fix 1: Data Rows col >= 7 and alignment wraps
search1 = '''            for col in range(2, 12):
                cell = ws.cell(row=row, column=col)
                cell.font = ARIAL_11
                cell.border = get_border(col)
                cell.alignment = Alignment(vertical="center")
                if col >= 5:
                    cell.number_format = _NUM_FMT
                    cell.alignment = ALIGN_RIGHT
            
            ws.cell(row=row, column=2).alignment = ALIGN_CENTER
            ws.cell(row=row, column=3).alignment = ALIGN_WRAP
            ws.cell(row=row, column=4).alignment = ALIGN_WRAP'''

replace1 = '''            for col in range(2, 12):
                cell = ws.cell(row=row, column=col)
                cell.font = ARIAL_11
                cell.border = get_border(col)
                cell.alignment = Alignment(vertical="center")
                if col >= 7:
                    cell.number_format = _NUM_FMT
                    cell.alignment = ALIGN_RIGHT
            
            ws.cell(row=row, column=2).alignment = ALIGN_CENTER
            ws.cell(row=row, column=5).alignment = ALIGN_WRAP
            ws.cell(row=row, column=6).alignment = ALIGN_WRAP'''
exports_content = exports_content.replace(search1, replace1)


# Fix 2: Subtotal row col >= 7
search2 = '''        for col in range(2, 12):
            cell = ws.cell(row=row, column=col)
            cell.fill = YELLOW_FILL
            cell.font = ARIAL_11_BOLD
            cell.border = get_border(col)
            cell.alignment = Alignment(vertical="center")
            if col >= 5:
                cell.number_format = _NUM_FMT
                cell.alignment = ALIGN_RIGHT'''
replace2 = '''        for col in range(2, 12):
            cell = ws.cell(row=row, column=col)
            cell.fill = YELLOW_FILL
            cell.font = ARIAL_11_BOLD
            cell.border = get_border(col)
            cell.alignment = Alignment(vertical="center")
            if col >= 7:
                cell.number_format = _NUM_FMT
                cell.alignment = ALIGN_RIGHT'''
exports_content = exports_content.replace(search2, replace2)

# Fix 3: Grand Total row col >= 7
search3 = '''    for col in range(2, 12):
        cell = ws.cell(row=row, column=col)
        cell.fill = DARK_BLUE_FILL
        cell.font = ARIAL_11_WHITE_BOLD
        cell.border = get_border(col)
        cell.alignment = Alignment(vertical="center")
        if col >= 5:
            cell.number_format = _NUM_FMT
            cell.alignment = ALIGN_RIGHT'''
replace3 = '''    for col in range(2, 12):
        cell = ws.cell(row=row, column=col)
        cell.fill = DARK_BLUE_FILL
        cell.font = ARIAL_11_WHITE_BOLD
        cell.border = get_border(col)
        cell.alignment = Alignment(vertical="center")
        if col >= 7:
            cell.number_format = _NUM_FMT
            cell.alignment = ALIGN_RIGHT'''
exports_content = exports_content.replace(search3, replace3)


# Fix 4: PCT Allocation append
search4 = '''    ws.append(["", 
        "% Allocation", "", "",
        f"{pct['app_amount']}%", f"{pct['energy_finance_amount']}%", f"{pct['property_amount']}%", f"{pct['agri_amount']}%", ""
    ])'''
replace4 = '''    ws.append(["", 
        "% Allocation", "", "", "", "",
        f"{pct['app_amount']}%", f"{pct['energy_finance_amount']}%", f"{pct['property_amount']}%", f"{pct['agri_amount']}%", ""
    ])'''
exports_content = exports_content.replace(search4, replace4)


# Fix 5: PCT Allocation col >= 7 and merge cells
search5 = '''    for col in range(2, 10):
        cell = ws.cell(row=row, column=col)
        cell.font = Font(name='Arial', size=11, italic=True)
        cell.border = get_border(col)
        cell.alignment = Alignment(vertical="center")
        if col >= 5:
            cell.alignment = ALIGN_RIGHT
    
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)'''
replace5 = '''    for col in range(2, 12):
        cell = ws.cell(row=row, column=col)
        cell.font = Font(name='Arial', size=11, italic=True)
        cell.border = get_border(col)
        cell.alignment = Alignment(vertical="center")
        if col >= 7:
            cell.alignment = ALIGN_RIGHT
    
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)'''
exports_content = exports_content.replace(search5, replace5)


with open(exports_path, 'w', encoding='utf-8') as f:
    f.write(exports_content)
print("exports.py patched perfectly!")
