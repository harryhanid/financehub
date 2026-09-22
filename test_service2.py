from app.modules.sahabat_etf.service import get_family_summary
from app import create_app

def test():
    try:
        # Just manually load from service
        import sqlite3
        conn = sqlite3.connect('app/finance_hub.db')
        conn.row_factory = sqlite3.Row
        
        company_id = 1
        PROGRAM_NAME = "Sahabat ETF"
        
        siswa_rows = conn.execute(f"""
            SELECT s.code AS siswa_code, s.nama,
                   (SELECT SUM(b.amount) FROM budget_beasiswa b WHERE b.siswa_code = s.code AND b.company_id = s.company_id ) AS budget_total,
                   (SELECT SUM(p.amount) FROM payment_beasiswa p WHERE p.siswa_code = s.code AND p.company_id = s.company_id AND p.status = 'complete' ) AS realisasi_total
            FROM siswa s
            WHERE s.company_id = ? AND s.program = ?
        """, (company_id, PROGRAM_NAME)).fetchall()
        
        print(f"siswa_rows count: {len(siswa_rows)}")
        
        # Now let's just see if get_family_summary crashes when called through app context
        app = create_app()
        with app.app_context():
            f = get_family_summary(company_id, [], [])
            print(f"families count: {len(f)}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()

test()
