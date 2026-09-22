import sqlite3
import json

conn = sqlite3.connect('C:/Financehub/app/db/finance.db')
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT id, siswa_code, pam_number, nominal, kategori_2 FROM payment_beasiswa WHERE pam_number LIKE 'PAM-114%' AND siswa_code = '3180066'").fetchall()

print(json.dumps([dict(r) for r in rows], indent=2))
