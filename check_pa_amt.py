import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, pa_id, student_id, jumlah_pembayaran FROM setf_pa_lines WHERE jumlah_pembayaran IN (5048769, 36175253)")
for r in cur.fetchall():
    print(dict(r))
