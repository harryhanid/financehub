from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from auth.middleware import jwt_html_required, json_required
from database import get_conn
import pandas as pd
import sqlite3
import os
import re
import pythoncom
import win32com.client

bp = Blueprint("general_ledger", __name__, url_prefix="/general-ledger")

SHEET_TABLE_MAPPING = {
    "GL SMT": "GLSMT",
    "GL ETF": "GLETF",
    "GL SETF": "GLSETF",
    "GL SME": "GLSME"
}

def clean_col_name(col):
    col = str(col).lower()
    col = re.sub(r'[^a-z0-9]', '_', col)
    col = re.sub(r'_+', '_', col)
    return col.strip('_')

@bp.route("/", methods=["GET"])
@jwt_html_required
def index():
    company_code = session.get("company_code", "SMT") # Default fallback
    conn = get_conn()
    
    # Mapping dari company code session ke table name
    company_table_map = {
        "SMT": "GLSMT",
        "ETF": "GLETF",
        "SETF": "GLSETF",
        "SME": "GLSME"
    }
    
    table_name = company_table_map.get(company_code, "GLSMT")
    
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        # Get last 100 records for preview without assuming id_gl primary key
        rows = conn.execute(f"SELECT * FROM {table_name} LIMIT 100").fetchall()
        columns = [description[0] for description in conn.execute(f"SELECT * FROM {table_name} LIMIT 1").cursor.description]
    except Exception as e:
        count = 0
        rows = []
        columns = []
    finally:
        conn.close()
        
    return render_template("general_ledger/index.html", count=count, rows=rows, columns=columns, active_company=company_code, target_table=table_name)

@bp.route("/sync", methods=["POST"])
@json_required
def sync_data():
    pythoncom.CoInitialize()
    try:
        try:
            excel = win32com.client.GetActiveObject("Excel.Application")
        except Exception:
            return jsonify({"ok": False, "pesan": "Aplikasi Excel tidak terdeteksi berjalan. Silakan buka file 'GL - MASTER' di Excel terlebih dahulu."})
            
        target_wb = None
        for wb in excel.Workbooks:
            if wb.Name and "GL - MASTER" in wb.Name.upper():
                target_wb = wb
                break
                
        if not target_wb:
            return jsonify({"ok": False, "pesan": "File Excel dengan nama 'GL - MASTER' tidak ditemukan. Pastikan file tersebut sedang terbuka."})
            
        success_count = 0
        conn = sqlite3.connect(r'C:\Financehub\app\finance_hub.db')
        
        details = []
        
        for sheet_name, table_name in SHEET_TABLE_MAPPING.items():
            try:
                ws = target_wb.Sheets(sheet_name)
            except Exception:
                details.append(f"Sheet '{sheet_name}' tidak ditemukan.")
                continue
                
            # Menggunakan pandas untuk membaca data dari Excel COM
            data = ws.UsedRange.Value
            if not data or len(data) < 2:
                details.append(f"Sheet '{sheet_name}' kosong atau kurang dari 2 baris.")
                continue
                
            headers = data[0]
            rows = data[1:]
            
            df = pd.DataFrame(rows, columns=headers)
            # Drop empty columns
            df = df.loc[:, df.columns.notna() & (df.columns != '')]
            
            df.columns = [clean_col_name(c) for c in df.columns]
            
            # Format datetime
            for col in df.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                df[col] = df[col].astype(str)
                
            # Truncate data lama
            try:
                conn.execute(f"DELETE FROM {table_name}")
            except sqlite3.OperationalError:
                pass # Table doesn't exist yet, to_sql will create it
                
            df.to_sql(table_name, conn, if_exists='append', index=False)
            success_count += len(df)
            details.append(f"Sheet '{sheet_name}' -> Tabel '{table_name}': {len(df)} baris.")
            
        conn.commit()
        conn.close()
        
        if success_count == 0:
            return jsonify({"ok": False, "pesan": "Tidak ada data yang berhasil ditarik.\n" + "\n".join(details)})
            
        return jsonify({"ok": True, "pesan": f"Berhasil sinkronisasi total {success_count} baris data GL dari Excel aktif!\n\n" + "\n".join(details)})
        
    except Exception as e:
        return jsonify({"ok": False, "pesan": f"Error saat menarik data: {str(e)}"})
    finally:
        pythoncom.CoUninitialize()
