import re

file_path = "C:/Financehub/app/modules/sahabat_etf/routes.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace('result["yearly"] = get_yearly_breakdown(_cid(), pillars)', 'result["yearly"] = get_yearly_breakdown(_cid(), years, pillars)')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
