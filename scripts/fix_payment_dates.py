"""
fix_payment_dates.py — Perbaiki tgl_pengajuan/receive/pa/final di payment_beasiswa
yang tidak ter-migrate saat import pertama kali.

Strategi:
  1. cat4 di DB berisi nilai tgl_pengajuan (datetime string dengan time component)
     → pindahkan ke tgl_pengajuan, bersihkan cat4
  2. tgl_receive / tgl_pa / tgl_final belum ada → baca ulang Excel, match by
     (siswa_code, tanggal, amount_rounded, cat1, cat2) dan update per-row.

Jalankan dari folder C:\\Financehub:
    python scripts\\fix_payment_dates.py
"""
import sys
import os
import sqlite3
from datetime import datetime, date
from collections import defaultdict

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl belum terinstall. Jalankan: pip install openpyxl")
    sys.exit(1)

EXCEL_PATH = r"C:\Users\25010160\Downloads\2026 DbBeasiswa v2.2.xlsm"
DB_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "finance_hub.db")
COMPANY_ID = 2


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
    # Strip time component if present (e.g. "2026-01-12 00:00:00")
    if " " in s:
        s = s.split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s


def fix():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # ── Step 1: Pindahkan cat4 → tgl_pengajuan ──────────────────────────────
    # cat4 yang berisi tanggal berbentuk "YYYY-MM-DD HH:MM:SS" atau "YYYY-MM-DD"
    cur = conn.execute(
        """SELECT id, cat4 FROM payment_beasiswa
           WHERE company_id=? AND cat4 IS NOT NULL AND cat4 != ''
             AND tgl_pengajuan IS NULL""",
        (COMPANY_ID,)
    )
    rows_cat4 = cur.fetchall()
    step1_updated = 0
    for r in rows_cat4:
        cleaned = safe_date(r["cat4"])
        if cleaned:
            conn.execute(
                "UPDATE payment_beasiswa SET tgl_pengajuan=?, cat4='' WHERE id=?",
                (cleaned, r["id"])
            )
            step1_updated += 1

    conn.commit()
    print(f"Step 1: {step1_updated} baris cat4 -> tgl_pengajuan dipindahkan.")

    # ── Step 2: Isi tgl_receive / tgl_pa / tgl_final dari Excel ─────────────
    # Build lookup dari DB: key=(siswa_code, tanggal, amount_int, cat1, cat2)
    # → list of row ids yang belum punya tgl_receive (urutan insert)
    cur2 = conn.execute(
        """SELECT id, siswa_code, tanggal, amount, cat1, cat2
           FROM payment_beasiswa
           WHERE company_id=? AND tgl_receive IS NULL
           ORDER BY id""",
        (COMPANY_ID,)
    )
    db_rows = cur2.fetchall()

    # Group by key → deque of ids
    from collections import deque
    pending = defaultdict(deque)
    for r in db_rows:
        key = (
            str(r["siswa_code"]),
            r["tanggal"] or "",
            round(float(r["amount"] or 0)),
            (r["cat1"] or "").strip(),
            (r["cat2"] or "").strip(),
        )
        pending[key].append(r["id"])

    print(f"Step 2: {len(db_rows)} baris DB menunggu update tgl_receive/pa/final.")

    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, keep_vba=False, data_only=True)
    ws = wb["DbPayment"]

    updated = 0
    no_match = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        if len(row) < 13:
            continue

        cat5 = safe_date(row[12]) if len(row) > 12 else ""
        cat6 = safe_date(row[13]) if len(row) > 13 else ""
        cat7 = safe_date(row[14]) if len(row) > 14 else ""

        # Skip rows without any of these dates
        if not any([cat5, cat6, cat7]):
            continue

        raw_code = row[0]
        code = str(int(raw_code)) if isinstance(raw_code, (int, float)) else safe_str(raw_code)
        if not code:
            continue

        tanggal = safe_date(row[3])
        amount  = safe_float(row[4])
        cat1    = safe_str(row[1]).strip()
        cat2    = safe_str(row[2]).strip()

        key = (code, tanggal, round(amount), cat1, cat2)

        if not pending[key]:
            no_match += 1
            continue

        row_id = pending[key].popleft()
        conn.execute(
            """UPDATE payment_beasiswa
               SET tgl_receive=?, tgl_pa=?, tgl_final=?
               WHERE id=?""",
            (cat5 or None, cat6 or None, cat7 or None, row_id)
        )
        updated += 1
        if updated % 100 == 0:
            conn.commit()
            print(f"  {updated} baris diupdate...")

    conn.commit()
    wb.close()
    conn.close()

    print(f"\nStep 2 selesai:")
    print(f"  tgl_receive/pa/final diupdate : {updated}")
    print(f"  Tidak cocok (no_match)        : {no_match}")
    print("\nVerifikasi — jalankan:")
    print("  python -c \"import sqlite3; c=sqlite3.connect('app/finance_hub.db'); "
          "r=c.execute('SELECT COUNT(*),SUM(CASE WHEN tgl_pengajuan IS NOT NULL THEN 1 ELSE 0 END),"
          "SUM(CASE WHEN tgl_receive IS NOT NULL THEN 1 ELSE 0 END) FROM payment_beasiswa').fetchone(); "
          "print(r); c.close()\"")


if __name__ == "__main__":
    fix()
