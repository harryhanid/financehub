import os

js_path = r'C:\Financehub\app\static\js\sponsorship.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

search = '''    html += '<tr class="sp-report-subtotal-row"><td colspan="3">TOTAL ' +'''
replace = '''    html += '<tr class="sp-report-subtotal-row"><td colspan="5">TOTAL ' +'''
js_content = js_content.replace(search, replace)

search2 = '''  html += '<tr class="sp-report-subtotal-row"><td colspan="3">TOTAL SPONSORSHIP (ACTUAL)</td>' +'''
replace2 = '''  html += '<tr class="sp-report-subtotal-row"><td colspan="5">TOTAL SPONSORSHIP (ACTUAL)</td>' +'''
js_content = js_content.replace(search2, replace2)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)
print("sponsorship.js patched")


exports_path = r'C:\Financehub\app\modules\sponsorship\exports.py'
with open(exports_path, 'r', encoding='utf-8') as f:
    ex_content = f.read()

s3 = '''        ws.append(["", 
            f"TOTAL {section['description'].upper()}", "", "",
            sub["app_amount"], sub["energy_finance_amount"], sub["property_amount"], sub["agri_amount"], sub["total"]
        ])'''
r3 = '''        ws.append(["", 
            f"TOTAL {section['description'].upper()}", "", "", "", "",
            sub["app_amount"], sub["energy_finance_amount"], sub["property_amount"], sub["agri_amount"], sub["total"]
        ])'''
ex_content = ex_content.replace(s3, r3)

s4 = '''    ws.append(["", 
        "TOTAL SPONSORSHIP (ACTUAL)", "", "",
        gt["app_amount"], gt["energy_finance_amount"], gt["property_amount"], gt["agri_amount"], gt["total"]
    ])'''
r4 = '''    ws.append(["", 
        "TOTAL SPONSORSHIP (ACTUAL)", "", "", "", "",
        gt["app_amount"], gt["energy_finance_amount"], gt["property_amount"], gt["agri_amount"], gt["total"]
    ])'''
ex_content = ex_content.replace(s4, r4)

s5 = '''        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)'''
r5 = '''        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)'''
ex_content = ex_content.replace(s5, r5)

with open(exports_path, 'w', encoding='utf-8') as f:
    f.write(ex_content)
print("exports.py patched")
