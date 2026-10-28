import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM setf_pa WHERE nomor_pam='PAM-019-SETF-08-2026'")
for r in cur.fetchall():
    print(dict(r))
