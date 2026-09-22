import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'x: \{\s*stacked: true,\s*ticks: \{ color: textColor \},\s*grid: \{ color: gridColor \}\s*\}'
repl = 'x: {\n            stacked: true,\n            ticks: { color: textColor, padding: 16 },\n            grid: { color: gridColor }\n        }'

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Added padding to X axis ticks!")
