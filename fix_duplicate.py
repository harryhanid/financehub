import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'const setfGroupedSublabelPlugin = \{[\s\S]*?ctx\.restore\(\);\s*\}\s*\};\s*const setfGroupedSublabelPlugin = \{'
repl = 'const setfGroupedSublabelPlugin = {'
content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Removed duplicate plugin!")
