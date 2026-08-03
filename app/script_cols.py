import sqlite3
conn = sqlite3.connect(r"C:\Financehub\app\finance_hub.db")
c = conn.cursor()
c.execute("PRAGMA table_info(sponsorship_transaksi)")
cols = [r[1] for r in c.fetchall()]
print(cols)
conn.close()
