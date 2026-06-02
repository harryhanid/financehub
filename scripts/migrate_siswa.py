"""
migrate_siswa.py — Import data siswa dari Excel ke Finance Hub SQLite (ETF)
Jalankan dari folder C:\Financehub\app:
    python ..\scripts\migrate_siswa.py
"""
import sys
import os
import sqlite3
from datetime import datetime

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl belum terinstall. Jalankan: pip install openpyxl")
    sys.exit(1)

EXCEL_PATH = r"C:\Users\25010160\Downloads\2026 DbBeasiswa v2.2.xlsm"
DB_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "finance_hub.db")
COMPANY_ID = 2  # ETF

STATUS_MAP = {
    "aktif":      "Aktif",
    "lulus":      "lulus",
    "gugur":      "gugur",
    "undur diri": "undur diri",
    "meninggal":  "meninggal",
    "":           "Aktif",
}


def safe_float(val):
    try:
        f = float(str(val).replace(",", "").strip())
        return f if f > 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def safe_str(val):
    if val is None or val == 0:
        return ""
    s = str(val).strip()
    return "" if s in ("0", "None") else s


def ts():
    return datetime.now().isoformat(timespec="seconds")


def migrate():
    print(f"Membuka Excel: {EXCEL_PATH}")
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, keep_vba=False, data_only=True)
    ws = wb["DbSiswa"]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    inserted = 0
    skipped  = 0
    errors   = []

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    total = sum(1 for r in rows if r[0])
    print(f"Total baris data: {total}\n")

    for i, row in enumerate(rows):
        if not row[0]:
            continue

        code = str(int(row[0])) if isinstance(row[0], (int, float)) else safe_str(row[0])
        if not code:
            continue

        # Cek duplikat
        exists = conn.execute(
            "SELECT id FROM siswa WHERE company_id=? AND code=?", (COMPANY_ID, code)
        ).fetchone()
        if exists:
            skipped += 1
            continue

        nama       = safe_str(row[1])
        jenjang    = safe_str(row[2])
        angkatan   = int(row[3]) if row[3] and str(row[3]).isdigit() else (int(row[3]) if isinstance(row[3], (int, float)) else None)
        program    = safe_str(row[4])
        fakultas   = safe_str(row[5])
        universitas= safe_str(row[6])
        bank       = safe_str(row[7])
        norek      = safe_str(row[8])
        namarek    = safe_str(row[9])
        referensi  = safe_str(row[10])
        ipk_sem    = [safe_float(row[11 + j]) for j in range(10)]
        ipk_pen    = [safe_float(row[21 + j]) for j in range(3)]
        status_raw = safe_str(row[24]).lower()
        status     = STATUS_MAP.get(status_raw, "Aktif")
        catatan    = safe_str(row[25])

        try:
            conn.execute(
                """INSERT INTO siswa
                   (company_id, code, nama, jenjang, angkatan, program, fakultas, universitas,
                    bank, norek, namarek, referensi,
                    ipk_sem1,ipk_sem2,ipk_sem3,ipk_sem4,ipk_sem5,
                    ipk_sem6,ipk_sem7,ipk_sem8,ipk_sem9,ipk_sem10,
                    ipk_pen1,ipk_pen2,ipk_pen3,
                    status, catatan, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (COMPANY_ID, code, nama, jenjang, angkatan, program, fakultas, universitas,
                 bank, norek, namarek, referensi,
                 *ipk_sem, *ipk_pen,
                 status, catatan, ts())
            )
            inserted += 1
            if inserted % 100 == 0:
                print(f"  {inserted}/{total} baris diimport...")
        except Exception as e:
            errors.append(f"Code {code}: {e}")

    conn.commit()
    conn.close()
    wb.close()

    print(f"\n✅ Selesai!")
    print(f"   Berhasil diimport : {inserted}")
    print(f"   Sudah ada (skip)  : {skipped}")
    print(f"   Error             : {len(errors)}")
    if errors:
        print("\nError detail:")
        for err in errors[:10]:
            print(f"  - {err}")


if __name__ == "__main__":
    migrate()
