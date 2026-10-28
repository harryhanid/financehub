import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT siswa_code FROM siswa WHERE id IN (1238, 3831)")
codes = [r["siswa_code"] for r in cur.fetchall()]
print(f"Codes: {codes}")
for code in codes:
    cur.execute(f"SELECT id, pam, payment_id FROM klaim_medical WHERE siswa_code='{code}'")
    for r in cur.fetchall():
        print(f"klaim: {dict(r)}")
