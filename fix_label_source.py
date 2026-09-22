import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target1 = r'const label = tick\.label;'
replacement1 = """const label = chart.data.labels[idx];"""

content = content.replace(target1, replacement1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
