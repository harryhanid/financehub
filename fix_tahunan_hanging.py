import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

junk = r'[\s\n]*setfRenderStackedGroupedChart\("chart-tahunan-kategori", yearly\.years, yearly\.kategori\);[\s\n]*setfRenderStackedGroupedChart\("chart-tahunan-pillar", yearly\.years, yearly\.pillar\);[\s\n]*setfRenderTotalTable\("setf-tahunan-kategori-table", yearly\.kategori\);[\s\n]*setfRenderTotalTable\("setf-tahunan-pillar-table", yearly\.pillar\);\n\}'

match = re.search(junk, content)
if match:
    print("Found hanging block for Tahunan! Removing...")
    content = content[:match.start()] + "\n" + content[match.end():]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
else:
    print("Could not find hanging block.")
