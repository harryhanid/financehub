"""
One-off fix: payment_beasiswa.etf_pa_line_id salah kena FOREIGN KEY ke
etf_pa_lines(id) — padahal kolom ini dipakai lintas pillar (AGRI/APP/LAND/
SETF/ENERGY), masing-masing punya tabel *_pa_lines sendiri dengan id yang
tidak nyambung ke etf_pa_lines. Makanya simpan PAM untuk pillar selain
AGRI (contoh: SETF) yang terhubung ke PA gagal dengan
"FOREIGN KEY constraint failed".

Fix: rebuild tabel payment_beasiswa TANPA FK di kolom etf_pa_line_id
(sesuai desain aslinya di database.py — CREATE TABLE fresh tidak punya FK
ini sama sekali). Semua data & kolom lain dipertahankan persis.

CARA PAKAI:
  1. STOP dulu server Flask yang lagi jalan (biar tidak ada yang nulis
     bersamaan pas proses rebuild).
  2. Jalankan: python fix_etf_pa_line_id_fk.py
  3. Nyalakan lagi servernya.
"""
import shutil
import sqlite3
import sys
from datetime import datetime

DB_PATH = "finance_hub.db"

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S") if False else None
# Date.now()-style calls avoided; use a fixed literal instead so this
# script is safe to re-run without surprises.
BACKUP_SUFFIX = "bak_fix_etf_pa_line_id_fk"

NEW_TABLE_SQL = """
CREATE TABLE payment_beasiswa_new (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    siswa_code      TEXT NOT NULL,
    cat1            TEXT,
    cat2            TEXT,
    tanggal         TEXT,
    amount          REAL DEFAULT 0,
    pillar          TEXT,
    pam             TEXT,
    perusahaan      TEXT,
    cat3            TEXT,
    cat4            TEXT,
    memo_id         INTEGER REFERENCES payment_memo(id),
    status          TEXT DEFAULT 'draft',
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    tgl_pengajuan   TEXT,
    tgl_receive     TEXT,
    tgl_pa          TEXT,
    tgl_final       TEXT,
    "tgl_retur"        TEXT,
    "tgl_final6"       TEXT,
    "tgl_proses"       TEXT,
    "SLA_Date_2_HT"    TEXT,
    "SLA_Date_3_YK"    TEXT,
    "SLA_Date_4_AK"    TEXT,
    "SLA_Date_5_PD"    TEXT,
    "SLA_Date_6_C2"    TEXT,
    "SLA_Date_7_MSIG"  TEXT,
    "tgl_A-GS_APP"     TEXT,
    "tgl_A-HJK_APP"    TEXT,
    "tgl_ASPIRO_APP"   TEXT,
    "tgl_Paid_APP"     TEXT,
    etf_pa_line_id     INTEGER,
    "tgl_Paid_LAND"    TEXT,
    "tgl_Paid_ENERGY"  TEXT,
    "tgl_Paid_SETF"    TEXT,
    "SLA_Date_1_LL"    TEXT
)
"""

COLUMNS = [
    "id", "company_id", "siswa_code", "cat1", "cat2", "tanggal", "amount",
    "pillar", "pam", "perusahaan", "cat3", "cat4", "memo_id", "status",
    "created_at", "tgl_pengajuan", "tgl_receive", "tgl_pa", "tgl_final",
    "tgl_retur", "tgl_final6", "tgl_proses", "SLA_Date_2_HT",
    "SLA_Date_3_YK", "SLA_Date_4_AK", "SLA_Date_5_PD", "SLA_Date_6_C2",
    "SLA_Date_7_MSIG", "tgl_A-GS_APP", "tgl_A-HJK_APP", "tgl_ASPIRO_APP",
    "tgl_Paid_APP", "etf_pa_line_id", "tgl_Paid_LAND", "tgl_Paid_ENERGY",
    "tgl_Paid_SETF", "SLA_Date_1_LL",
]


def main():
    import time
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = f"{DB_PATH}.{BACKUP_SUFFIX}_{stamp}"
    print(f"1. Backup {DB_PATH} -> {backup_path}")
    shutil.copy2(DB_PATH, backup_path)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")

    before = conn.execute(
        "SELECT COUNT(*) FROM payment_beasiswa"
    ).fetchone()[0]
    print(f"2. Baris di payment_beasiswa sebelum rebuild: {before}")

    col_list = ", ".join(f'"{c}"' if not c.isidentifier() else c for c in COLUMNS)

    conn.execute("BEGIN")
    try:
        conn.execute("DROP TABLE IF EXISTS payment_beasiswa_new")
        conn.execute(NEW_TABLE_SQL)
        conn.execute(
            f"INSERT INTO payment_beasiswa_new ({col_list}) "
            f"SELECT {col_list} FROM payment_beasiswa"
        )
        conn.execute("DROP TABLE payment_beasiswa")
        conn.execute(
            "ALTER TABLE payment_beasiswa_new RENAME TO payment_beasiswa"
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    conn.execute("PRAGMA foreign_keys = ON")
    after = conn.execute("SELECT COUNT(*) FROM payment_beasiswa").fetchone()[0]
    fk_list = conn.execute(
        "PRAGMA foreign_key_list(payment_beasiswa)"
    ).fetchall()
    fk_check = conn.execute(
        "PRAGMA foreign_key_check(payment_beasiswa)"
    ).fetchall()
    conn.close()

    print(f"3. Baris setelah rebuild: {after} (harus sama dengan {before})")
    print("4. FK yang tersisa di payment_beasiswa:")
    for row in fk_list:
        print("   ", row)
    print(f"5. foreign_key_check (harus kosong []): {fk_check}")

    if after != before:
        print("!!! JUMLAH BARIS BEDA — cek backup, JANGAN dipakai dulu.")
        sys.exit(1)
    if any(row[2] == "etf_pa_lines" for row in fk_list):
        print("!!! FK ke etf_pa_lines masih ada — fix gagal.")
        sys.exit(1)

    print("\nSELESAI. Backup lama ada di:", backup_path)


if __name__ == "__main__":
    main()
