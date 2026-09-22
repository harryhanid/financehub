import re

file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'\(\"fam5\", \[\"5260001\"\]\),.*?\(\"fam7\", \[\"5230001\"\]\),\s*# Joshua Darren Chandra \(single\)\n'
replacement = ""
content = re.sub(target, replacement, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
