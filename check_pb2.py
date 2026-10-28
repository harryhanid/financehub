import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("PRAGMA table_info(payment_beasiswa)")
for r in cur.fetchall():
    print(dict(r)["name"])
