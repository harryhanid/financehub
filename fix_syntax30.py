file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

import re
start_idx = content.find("const setfTotalZonePlugin = {")
if start_idx != -1:
    content = content[:start_idx]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Wiped corrupted bottom chunk!")
