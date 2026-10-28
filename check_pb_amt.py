import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT amount, pam FROM payment_beasiswa WHERE id IN (9816, 9817)")
for r in cur.fetchall():
    print(dict(r))
