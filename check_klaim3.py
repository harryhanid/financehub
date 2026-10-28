import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM klaim_medical WHERE id IN (29, 30)")
for r in cur.fetchall():
    print(dict(r))
