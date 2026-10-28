import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT amount, etf_pa_line_id FROM payment_beasiswa WHERE pam='PAM-002-LAND-07-2026'")
for r in cur.fetchall():
    print(dict(r))
