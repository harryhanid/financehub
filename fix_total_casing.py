import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace('l === "Total"', 'l === "TOTAL"')
content = content.replace('lbl !== "Total"', 'lbl !== "TOTAL"')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed TOTAL casing!")
