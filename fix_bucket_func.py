import re

file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'def build_report_data\(company_id: int, report_year: int, report_month: int = 12, pillars: list = None\) -> dict:\n\s*buckets = _build_diagram_buckets\(company_id, \[str\(report_year\)\], report_month, pillars\)'
repl = 'def build_report_data(company_id: int, report_year: int, report_month: int = 12, pillars: list = None) -> dict:\n    buckets = _build_buckets(company_id, report_year, report_month, pillars)'

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed wrong bucket function in build_report_data!")
