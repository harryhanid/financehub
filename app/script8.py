import sqlite3
conn = sqlite3.connect(r"C:\Financehub\app\finance_hub.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(payment_beasiswa)")
print("payment_beasiswa columns:")
for c in cursor.fetchall():
    print(c[1])
cursor.execute("PRAGMA table_info(siswa)")
print("\nsiswa columns:")
for c in cursor.fetchall():
    print(c[1])
conn.close()
