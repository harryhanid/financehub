import re

file_path = "C:/Financehub/app/modules/sahabat_etf/service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'"total_realisasi": f\["total_realisasi"\],'
replacement = """"total_realisasi": f["total_realisasi"],
            "total_budget": f.get("total_budget", 0),"""
content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
