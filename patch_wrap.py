import os

exports_path = r'C:\Financehub\app\modules\sponsorship\exports.py'
with open(exports_path, 'r', encoding='utf-8') as f:
    exports_content = f.read()

search = '''            ws.cell(row=row, column=2).alignment = ALIGN_CENTER
            ws.cell(row=row, column=5).alignment = ALIGN_WRAP
            ws.cell(row=row, column=6).alignment = ALIGN_WRAP'''

replace = '''            ws.cell(row=row, column=2).alignment = ALIGN_CENTER
            ws.cell(row=row, column=3).alignment = ALIGN_WRAP
            ws.cell(row=row, column=4).alignment = ALIGN_WRAP
            ws.cell(row=row, column=5).alignment = ALIGN_WRAP
            ws.cell(row=row, column=6).alignment = ALIGN_WRAP'''

if search in exports_content:
    exports_content = exports_content.replace(search, replace)
    with open(exports_path, 'w', encoding='utf-8') as f:
        f.write(exports_content)
    print("exports.py patched successfully")
else:
    print("search string not found in exports.py")

