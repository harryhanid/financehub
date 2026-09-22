import re

file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'buckets = _build_diagram_buckets\(company_id, years, month, pillars\)'
repl = 'buckets = _build_diagram_buckets(company_id, [str(report_year)], report_month, pillars)'

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed NameError in build_report_data!")
