import re

with open(r'app\tests\test_sahabat_etf_report_xlsx.py', 'r', encoding='utf-8') as f:
    content = f.read()

# _metrics definition
content = content.replace(
    'return {"plafon": plafon, "klaim": klaim, "dibayar": dibayar, "saldo": plafon - dibayar}',
    'return {"plafon": plafon, "pta": 0.0, "klaim": klaim, "dibayar": dibayar, "saldo": plafon - dibayar}'
)

# pct dicts
content = content.replace(
    '"pct_cur": {"plafon": 1.0, "klaim": 1.0, "dibayar": 1.0, "saldo": 1.0}',
    '"pct_cur": {"plafon": 1.0, "pta": 0.0, "klaim": 1.0, "dibayar": 1.0, "saldo": 1.0}'
)
content = content.replace(
    '"pct_cum": {"plafon": 1.0, "klaim": 1.0, "dibayar": 1.0, "saldo": 1.0}',
    '"pct_cum": {"plafon": 1.0, "pta": 0.0, "klaim": 1.0, "dibayar": 1.0, "saldo": 1.0}'
)

with open(r'app\tests\test_sahabat_etf_report_xlsx.py', 'w', encoding='utf-8') as f:
    f.write(content)
