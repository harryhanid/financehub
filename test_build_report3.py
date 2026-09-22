import sys
sys.path.insert(0, "C:/Financehub/app")

from modules.sahabat_etf.service import build_report_data

try:
    data = build_report_data(company_id=1, report_year=2027, report_month=12, pillars=None)
    print("SUCCESS! Built report data successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
