import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'    if \(typeof pattern === \'undefined\'\) \{[\s\S]*?return;\n    \}'
repl = ''

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Removed patternomaly fallback!")
