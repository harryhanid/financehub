import sqlite3
import json

db_path = 'app/finance_hub.db'
PROGRAM_NAME = "Sahabat ETF"

def _siswa_kategori_map(conn, company_id, years, pillars):
    return {}

def test_get_family_summary():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    company_id = 1
    
    budget_year_sql = " AND strftime('%Y', b.tanggal) = '2026'"
    payment_year_sql = " AND strftime('%Y', p.tanggal) = '2026'"
    
    siswa_rows = conn.execute(f"""
        SELECT s.code AS siswa_code, s.nama,
               (SELECT SUM(b.amount) FROM budget_beasiswa b WHERE b.siswa_code = s.code AND b.company_id = s.company_id {budget_year_sql}) AS budget_total,
               (SELECT SUM(p.amount) FROM payment_beasiswa p WHERE p.siswa_code = s.code AND p.company_id = s.company_id AND p.status = 'complete' {payment_year_sql}) AS realisasi_total
        FROM siswa s
        WHERE s.company_id = ? AND s.program = ?
    """, (company_id, PROGRAM_NAME)).fetchall()
    
    print(f"siswa_rows: {len(siswa_rows)}")

test_get_family_summary()
