import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, etf_pa_line_id, pillar, status FROM payment_beasiswa WHERE pam='PAM-019-SETF-08-2026'")
rows = cur.fetchall()
print(f"payment_beasiswa rows: {len(rows)}")
for r in rows:
    print(dict(r))
