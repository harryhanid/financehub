file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

import re
for i, line in enumerate(lines):
    if "api/breakdown" in line:
        for j in range(i, i+30):
            print(f"{j+1}: {lines[j].strip('\n')}")
        break
