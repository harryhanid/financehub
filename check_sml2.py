import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, status FROM sml_pa WHERE id IN (25, 26, 27, 28, 29)")
for r in cur.fetchall():
    print(dict(r))
