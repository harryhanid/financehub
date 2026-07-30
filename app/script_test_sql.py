import sqlite3
conn = sqlite3.connect(r"C:\Financehub\app\finance_hub.db")
c = conn.cursor()
c.execute("""
    SELECT p.tanggal, s.nama, p.cat1, p.cat2, p.amount
    FROM payment_beasiswa p
    JOIN siswa s ON s.code = p.siswa_code AND s.company_id = p.company_id
    WHERE p.status = 'complete'
    ORDER BY p.id DESC
    LIMIT 20
""")
rows = c.fetchall()
print("Total rows:", len(rows))
for r in rows:
    print(r)
conn.close()
