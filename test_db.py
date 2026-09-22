import sqlite3
import json

db_path = 'app/finance_hub.db'

def test():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Try the get_siswa_summary query
    rows = conn.execute("""
        SELECT s.code AS siswa_code, s.nama,
               (SELECT SUM(b.amount) FROM budget_beasiswa b WHERE b.siswa_code = s.code AND b.company_id = s.company_id) AS budget_total,
               (SELECT SUM(p.amount) FROM payment_beasiswa p WHERE p.siswa_code = s.code AND p.company_id = s.company_id AND p.status = 'complete') AS realisasi_total
        FROM siswa s
        WHERE s.company_id = 1 AND s.program = 'Sahabat ETF'
    """).fetchall()
    
    for r in rows:
        print(r['nama'], r['budget_total'], r['realisasi_total'])

test()
