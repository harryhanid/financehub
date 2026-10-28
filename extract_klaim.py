with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()
import re
match = re.search(r'function klaimAddSiswa.*?(?=function klaimRemoveSiswaGroup)', text, re.DOTALL)
if match:
    with open("klaim_functions.js", "w", encoding="utf-8") as f:
        f.write(match.group(0))
