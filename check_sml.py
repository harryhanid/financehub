import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, pa_id FROM sml_pa_lines WHERE id IN (28, 29)")
for r in cur.fetchall():
    print("sml_pa_lines", dict(r))
