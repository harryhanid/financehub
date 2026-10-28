import sys
import openpyxl

# Read Excel
downloads_dir = r"C:\Users\25010160\Downloads"
import os
files = [f for f in os.listdir(downloads_dir) if f.startswith('Sponsorship - MASTER') and f.endswith('.xlsx')]
files.sort(key=lambda x: os.path.getmtime(os.path.join(downloads_dir, x)), reverse=True)
latest_file = os.path.join(downloads_dir, files[0])

print(f"Reading {latest_file}")
wb = openpyxl.load_workbook(latest_file, data_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
print("Excel Row 2:", rows[1])

# DB check
app_dir = r"C:\Financehub\app"
sys.path.insert(0, app_dir)
from app import create_app
from database import get_conn

app = create_app()
with app.app_context():
    conn = get_conn()
    cur = conn.cursor()
    # Let's get the exact ID from Excel Row 2
    row2_id = rows[1][0]
    cur.execute("SELECT * FROM sponsorship_transaksi WHERE id = ?", (row2_id,))
    db_row = cur.fetchone()
    print("DB Row:", dict(db_row))

