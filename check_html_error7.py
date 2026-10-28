with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()
import re
match = re.search(r'function klaimAddSiswa.*?(?=function klaimRemoveSiswaGroup)', text, re.DOTALL)
if match:
    lines = match.group(0).split('\n')
    for i, l in enumerate(lines):
        if "hidEtfLineId" in l:
            print(f"Match line {i}: {l}")
