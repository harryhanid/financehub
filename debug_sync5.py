import sys
import openpyxl
import os

downloads_dir = r"C:\Users\25010160\Downloads"
target_file = os.path.join(downloads_dir, 'Sponsorship - MASTER.xlsx')

print(f"Reading {target_file}")
wb = openpyxl.load_workbook(target_file, data_only=True)
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
    cur.execute("SELECT * FROM sponsorship_transaksi WHERE company_id=1")
    db_rows = cur.fetchall()
    
    db_map = {r['id']: dict(r) for r in db_rows}
    
    diff_found = False
    for i, ex in enumerate(rows):
        ex_id = ex[0]
        if not ex_id:
            print(f"Row {i+2} in Excel has NO ID!")
            diff_found = True
            continue
            
        if ex_id not in db_map:
            print(f"Row {i+2} ID {ex_id} not in DB!")
            diff_found = True
            continue
            
        db_r = db_map[ex_id]
        
        mapping = [
            ('cat1', 5), ('cat2', 6), ('cat3', 7),
            ('tanggal_form_sponsor', 3), ('tanggal_payment', 4),
            ('cat', 1), ('description', 2), ('lembaga_perorangan', 8), ('perihal', 9),
            ('amount_request', 10), ('reff', 15), ('status', 16), ('cat4', 17),
            ('coa', 18), ('cc_total', 19), ('cc', 20), ('source', 21)
        ]
        for db_key, ex_idx in mapping:
            ex_val = ex[ex_idx]
            db_val = db_r[db_key]
            
            import datetime
            if isinstance(ex_val, datetime.datetime):
                ex_val = ex_val.strftime('%Y-%m-%d')
            
            if ex_val is None: ex_val = ""
            if db_val is None: db_val = ""
            if isinstance(ex_val, float) and ex_val == int(ex_val): ex_val = int(ex_val)
            if isinstance(db_val, float) and db_val == int(db_val): db_val = int(db_val)
            
            if str(ex_val).strip() != str(db_val).strip():
                if 'tanggal' in db_key and str(ex_val) in str(db_val):
                    continue
                print(f"Mismatch on ID {ex_id}, Column {db_key}: Excel='{ex_val}', DB='{db_val}'")
                diff_found = True

    if not diff_found:
        print("No differences found for Sponsorship - MASTER.xlsx!")
