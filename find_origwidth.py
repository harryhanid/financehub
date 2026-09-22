import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "const origWidth = parent.style.width;" in line:
        print(f"Line {i+1}: {line.strip()}")
