import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'const label = tick\.label;', 'const label = chart.data.labels[idx];', content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
