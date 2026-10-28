import os

exports_path = r'C:\Financehub\app\modules\sponsorship\exports.py'
with open(exports_path, 'r', encoding='utf-8') as f:
    exports_content = f.read()

search = '''    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 5
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 50
    ws.column_dimensions["E"].width = 20
    ws.column_dimensions["F"].width = 20
    ws.column_dimensions["G"].width = 22.08  # ~300 pixels
    ws.column_dimensions["H"].width = 20
    ws.column_dimensions["I"].width = 20'''

replace = '''    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 5
    ws.column_dimensions["C"].width = 15   # TANGGAL PAYMENT
    ws.column_dimensions["D"].width = 15   # REFF
    ws.column_dimensions["E"].width = 40   # LEMBAGA
    ws.column_dimensions["F"].width = 50   # PERIHAL
    ws.column_dimensions["G"].width = 20   # APP
    ws.column_dimensions["H"].width = 20   # ENERGY
    ws.column_dimensions["I"].width = 22.08 # PROPERTY
    ws.column_dimensions["J"].width = 20   # AGRI
    ws.column_dimensions["K"].width = 20   # TOTAL'''

if search in exports_content:
    exports_content = exports_content.replace(search, replace)
    with open(exports_path, 'w', encoding='utf-8') as f:
        f.write(exports_content)
    print("Column dimensions patched in exports.py")
else:
    print("search string not found!")

