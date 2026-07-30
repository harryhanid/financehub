import sqlite3

conn = sqlite3.connect(r"C:\Financehub\app\finance_hub.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(payment_beasiswa)")
columns = cursor.fetchall()
for col in columns:
    print(col[1])
conn.close()
