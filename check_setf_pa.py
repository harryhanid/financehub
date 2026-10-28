import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, pa_id FROM setf_pa_lines LIMIT 5")
for r in cur.fetchall():
    print(dict(r))

cur.execute("SELECT * FROM setf_pa WHERE nomor_pa='PA/SETF/027/2026'")
for r in cur.fetchall():
    print(dict(r))
