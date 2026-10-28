import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("PRAGMA table_info(setf_pa)")
columns = [r["name"] for r in cur.fetchall()]
print("Columns:", columns)
cur.execute("SELECT id, nomor_pam, status, tanggal_bayar FROM setf_pa WHERE nomor_pam='PAM-019-SETF-08-2026'")
for r in cur.fetchall():
    print(dict(r))
