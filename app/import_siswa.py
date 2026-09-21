import pandas as pd
import sqlite3
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_conn
from modules.beasiswa.service import add_siswa, generate_kode_siswa
import config

def to_float(val):
    if pd.isna(val): return 0.0
    val = str(val).strip()
    if not val or val == '-': return 0.0
    try:
        return float(val.replace(',', '.'))
    except:
        return 0.0

def import_excel(filepath, company_id=1):
    df = pd.read_excel(filepath)
    df = df.fillna("")
    
    success_count = 0
    error_count = 0
    errors = []

    for idx, row in df.iterrows():
        jenjang = str(row.get("Jenjang", "")).strip()
        angkatan = str(row.get("Angkatan", "")).strip()
        nama = str(row.get("Nama Lengkap", "")).strip()
        
        if not nama or nama == '-':
            continue
            
        if not jenjang or not angkatan.isdigit() or len(angkatan) != 4:
            errors.append(f"Row {idx+2}: '{nama}' - Jenjang & Angkatan (4 digit) tidak valid.")
            error_count += 1
            continue
            
        kode = generate_kode_siswa(jenjang, int(angkatan), company_id)
        
        # safely parse date
        tgl = str(row.get("Tanggal Lahir (YYYY-MM-DD)", "")).strip()
        if tgl == 'NaT' or tgl == '-': tgl = ''
        else: tgl = tgl[:10]
        
        data = {
            "code": kode,
            "nama": nama,
            "jenjang": jenjang,
            "angkatan": int(angkatan),
            "tanggal_lahir": tgl,
            "program": str(row.get("Program", "Sahabat ETF")).strip(),
            "group_setf": str(row.get("Group Sahabat", "")).strip(),
            "status": str(row.get("Status", "Aktif")).strip() or "Aktif",
            "prodi": str(row.get("Prodi", "")).strip(),
            "angkatan_kuliah": str(row.get("Angkatan Kuliah", "")).strip(),
            "fakultas": str(row.get("Fakultas", "")).strip(),
            "universitas": str(row.get("Universitas", "")).strip(),
            "bank": str(row.get("Bank", "")).strip(),
            "norek": str(row.get("No. Rekening", "")).strip(),
            "namarek": str(row.get("Nama Rekening", "")).strip(),
            "referensi": str(row.get("Referensi", "")).strip(),
            "catatan": str(row.get("Catatan", "")).strip(),
        }
        
        for i in range(1, 11):
            data[f"ipk_sem{i}"] = to_float(row.get(f"IPK Sem {i}", ""))
            
        for i in range(1, 4):
            data[f"ipk_pen{i}"] = to_float(row.get(f"IPK Pen {i}", ""))

        res = add_siswa(company_id, data)
        if res.get("ok"):
            success_count += 1
            print(f"[{success_count}] Berhasil insert: {nama} ({kode})")
        else:
            errors.append(f"Row {idx+2}: '{nama}' - Gagal: {res.get('pesan')}")
            error_count += 1

    print("\n--- HASIL IMPORT ---")
    print(f"Total Berhasil: {success_count}")
    print(f"Total Gagal: {error_count}")
    if errors:
        print("\nDaftar Error:")
        for e in errors:
            print("-", e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Penggunaan: python import_siswa.py <path_to_excel>")
    else:
        conn = get_conn()
        c = conn.execute("SELECT id FROM companies WHERE code='ETF' OR name LIKE '%ETF%'")
        row = c.fetchone()
        conn.close()
        cid = row[0] if row else 1
        
        import_excel(sys.argv[1], cid)
