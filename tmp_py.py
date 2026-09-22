import re

with open(r'app\modules\sahabat_etf\report_xlsx.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('\\"', '"')

with open(r'app\modules\sahabat_etf\report_xlsx.py', 'w', encoding='utf-8') as f:
    f.write(content)
