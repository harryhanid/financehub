import sys
sys.path.append(r"C:\Financehub\app")
from modules.beasiswa.service import get_dashboard_latest_payments

# Assuming company_id is 1 based on usual setups, but let's just query
import sqlite3
conn = sqlite3.connect(r"C:\Financehub\app\finance_hub.db")
c = conn.cursor()
c.execute("SELECT id FROM users LIMIT 1")
conn.close()

try:
    res = get_dashboard_latest_payments(1, years=[2023, 2024, 2025, 2026], limit=20)
    print("Found rows:", len(res))
    for r in res:
        print(r['tanggal'], r['nama'])
except Exception as e:
    print("Error:", e)
