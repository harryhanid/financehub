import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, pam_no, status, total_amount, tanggal_bayar FROM pam_records WHERE pam_no='PAM-002-LAND-07-2026'")
for r in cur.fetchall():
    print("PAM:", dict(r))
