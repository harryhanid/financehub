import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'y: \{\n\s*ticks: \{\n\s*padding: 22,'
repl = r'y: {\n            ticks: {'
content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Removed padding from Y axis!")
