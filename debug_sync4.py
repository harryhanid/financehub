import sys
import openpyxl
import os
import datetime

downloads_dir = r"C:\Users\25010160\Downloads"
files = [f for f in os.listdir(downloads_dir) if f.startswith('Sponsorship - MASTER') and f.endswith('.xlsx')]
files.sort(key=lambda x: os.path.getmtime(os.path.join(downloads_dir, x)), reverse=True)
latest_file = os.path.join(downloads_dir, files[0])

wb = openpyxl.load_workbook(latest_file, data_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))[1:]

app_dir = r"C:\Financehub\app"
sys.path.insert(0, app_dir)
from app import create_app
from database import get_conn

app = create_app()
with app.app_context():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sponsorship_transaksi WHERE company_id=1 AND strftime('%Y', tanggal_form_sponsor)='2026'")
    db_rows = cur.fetchall()
    
    db_map = {r['id']: dict(r) for r in db_rows}
    
    diff_found = False
    for i, ex in enumerate(rows):
        ex_id = ex[0]
        if ex_id not in db_map: continue
            
        db_r = db_map[ex_id]
        
        mapping = [
            ('cat1', 5), ('cat2', 6), ('cat3', 7),
            ('tanggal_form_sponsor', 3), ('tanggal_payment', 4)
        ]
        for db_key, ex_idx in mapping:
            ex_val = ex[ex_idx]
            db_val = db_r[db_key]
            
            if isinstance(ex_val, datetime.datetime):
                ex_val = ex_val.strftime('%Y-%m-%d')
            
            if ex_val is None: ex_val = ""
            if db_val is None: db_val = ""
            
            if str(ex_val).strip() != str(db_val).strip():
                # For dates, DB might have '2026-09-17 00:00:00'
                if 'tanggal' in db_key and str(ex_val) in str(db_val):
                    continue
                print(f"Mismatch on ID {ex_id}, Column {db_key}: Excel='{ex_val}', DB='{db_val}'")
                diff_found = True

    if not diff_found:
        print("No differences found for cat1/cat2/cat3/dates!")
