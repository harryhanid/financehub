import sqlite3
conn = sqlite3.connect("app/finance_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("UPDATE payment_beasiswa SET pillar = 'SETF' WHERE pam='PAM-002-LAND-07-2026'")
conn.commit()
print("Updated payment_beasiswa pillar to SETF")
