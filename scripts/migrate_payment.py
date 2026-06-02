"""
migrate_payment.py — Import data payment beasiswa dari Excel ke Finance Hub SQLite (ETF)
Jalankan dari folder C:\Financehub\app:
    python ..\scripts\migrate_payment.py
"""
import sys
import os
import sqlite3
from datetime import datetime, date

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl belum terinstall. Jalankan: pip install openpyxl")
    sys.exit(1)

EXCEL_PATH = r"C:\Users\25010160\Downloads\2026 DbBeasiswa v2.2.xlsm"
DB_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "finance_hub.db")
COMPANY_ID = 2  # ETF

# DbPayment columns:
# 0: Code  1: Cat1  2: Cat2  3: Date  4: Amount  5: Pillar
# 6: PAM   7: Perusahaan  8: PamUnique(skip)  9: Timestamp(skip)
# 10: Cat3  11: Cat4(=tgl_pengajuan)  12: Cat5(=tgl_receive)
# 13: Cat6(=tgl_pa)  14: Cat7(=tgl_final)


def safe_str(val):
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s in ("None", "0") else s


def safe_float(val):
    try:
        f = float(str(val).replace(",", "").strip())
        return f if f > 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def safe_date(val):
    if val is None:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s


def ts():
    return datetime.now().isoformat(timespec="seconds")


def migrate():
    print(f"Membuka Excel: {EXCEL_PATH}")
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, keep_vba=False, data_only=True)
    ws = wb["DbPayment"]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Collect valid siswa codes for lookup
    siswa_codes = {
        row[0] for row in conn.execute(
            "SELECT code FROM siswa WHERE company_id=?", (COMPANY_ID,)
        ).fetchall()
    }

    inserted  = 0
    skipped   = 0
    no_siswa  = 0
    errors    = []

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    total = sum(1 for r in rows if r[0])
    print(f"Total baris data (non-kosong): {total}\n")

    for row in rows:
        # Skip if Code (col 0) is empty
        if not row[0]:
            skipped += 1
            continue

        raw_code = row[0]
        code = str(int(raw_code)) if isinstance(raw_code, (int, float)) else safe_str(raw_code)
        if not code:
            skipped += 1
            continue

        # Skip if siswa not found in DB
        if code not in siswa_codes:
            no_siswa += 1
            continue

        cat1       = safe_str(row[1])
        cat2       = safe_str(row[2])
        tanggal    = safe_date(row[3])
        amount     = safe_float(row[4])
        pillar     = safe_str(row[5])
        pam        = safe_str(row[6])
        perusahaan = safe_str(row[7])
        cat3          = safe_str(row[10])  if len(row) > 10 else ""
        tgl_pengajuan = safe_date(row[11]) if len(row) > 11 else ""
        tgl_receive   = safe_date(row[12]) if len(row) > 12 else ""
        tgl_pa        = safe_date(row[13]) if len(row) > 13 else ""
        tgl_final     = safe_date(row[14]) if len(row) > 14 else ""

        if amount <= 0:
            skipped += 1
            continue

        try:
            conn.execute(
                """INSERT INTO payment_beasiswa
                   (company_id, siswa_code, cat1, cat2, tanggal, amount,
                    pillar, pam, perusahaan, cat3,
                    tgl_pengajuan, tgl_receive, tgl_pa, tgl_final,
                    status, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'approved',?)""",
                (COMPANY_ID, code, cat1, cat2, tanggal, amount,
                 pillar, pam, perusahaan, cat3,
                 tgl_pengajuan, tgl_receive, tgl_pa, tgl_final, ts())
            )
            inserted += 1
            if inserted % 500 == 0:
                conn.commit()
                print(f"  {inserted} baris diimport...")
        except Exception as e:
            errors.append(f"Code {code}: {e}")

    conn.commit()
    conn.close()
    wb.close()

    print("\nSelesai!")
    print(f"  Berhasil diimport  : {inserted}")
    print(f"  Skip (kosong/0)    : {skipped}")
    print(f"  Skip (siswa N/A)   : {no_siswa}")
    print(f"  Error              : {len(errors)}")
    if errors:
        print("\nError detail (max 10):")
        for err in errors[:10]:
            print(f"  - {err}")


if __name__ == "__main__":
    migrate()
