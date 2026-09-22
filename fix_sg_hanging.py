import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

junk_regex = r',\s*interaction: \{ mode: \'index\', intersect: false \},[\s\S]*?y: \{[\s\n]*stacked: true,[\s\S]*?\}\s*\}\s*\}\s*\);\s*\}'

match = re.search(junk_regex, content)
if match:
    print("Found hanging block for Stacked Grouped Chart! Removing...")
    content = content[:match.start()] + "\n" + content[match.end():]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
else:
    print("Could not find hanging block.")
