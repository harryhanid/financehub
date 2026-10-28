import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("PRAGMA table_info(rekam_medis)")
print("rekam_medis:", [r["name"] for r in cur.fetchall()])
cur.execute("PRAGMA table_info(klaim_medical)")
print("klaim_medical:", [r["name"] for r in cur.fetchall()])
