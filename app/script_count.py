import sqlite3
conn = sqlite3.connect(r"C:\Financehub\app\finance_hub.db")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM payment_beasiswa WHERE status = 'complete'")
print("Total complete payments:", cursor.fetchone()[0])
conn.close()
