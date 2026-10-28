import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT pam_no, source, pillar, status FROM pam_records WHERE pam_no LIKE '%SETF%' ORDER BY id DESC LIMIT 5")
for r in cur.fetchall():
    print(dict(r))
