import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, pa_number, status, nomor_pam FROM setf_pa WHERE status='on_process'")
for r in cur.fetchall():
    print(dict(r))
