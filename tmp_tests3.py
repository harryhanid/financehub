import re

with open(r'app\tests\test_sahabat_etf_report_xlsx.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'return {"plafon": 0.0, "klaim": 0.0, "dibayar": 0.0, "saldo": 0.0}',
    'return {"plafon": 0.0, "pta": 0.0, "klaim": 0.0, "dibayar": 0.0, "saldo": 0.0}'
)

with open(r'app\tests\test_sahabat_etf_report_xlsx.py', 'w', encoding='utf-8') as f:
    f.write(content)
