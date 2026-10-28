import os
import openpyxl
from datetime import datetime
import sqlite3

downloads_dir = os.path.expanduser('~\\Downloads')
files = [f for f in os.listdir(downloads_dir) if f.startswith('Sponsorship - MASTER') and f.endswith('.xlsx')]
files.sort(key=lambda x: os.path.getmtime(os.path.join(downloads_dir, x)), reverse=True)

latest_file = os.path.join(downloads_dir, files[0])
print(f"Reading {latest_file}")

wb = openpyxl.load_workbook(latest_file, data_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))

print("Total Rows in Excel:", len(rows))
if len(rows) > 1:
    print("Row 2:", rows[1])

# Let's compare with DB
db_path = r'C:\Financehub\app\financehub.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

cursor = conn.cursor()
cursor.execute("SELECT * FROM sponsorship_transaksi WHERE company_id=1 AND strftime('%Y', tanggal_form_sponsor)='2026' ORDER BY id ASC LIMIT 5")
db_rows = cursor.fetchall()
print("\nFirst 5 DB Rows for 2026:")
for r in db_rows:
    print(dict(r))

