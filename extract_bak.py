import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
file_path = "C:/Financehub/app/static/js/sahabat_etf.js.bak"

# 118MB file is large, so let's read it in blocks or find the first occurrence of `function setfRenderDiagram1`
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# The 118MB file has thousands of duplicated functions. We just need to find ONE occurrence of the diagram block!
# Let's search for `function setfLoadPohon`
match = re.search(r'(// --- Diagram Pohon ---[\s\S]*?)// \? Laporan tab', content)
if match:
    block = match.group(1)
    with open("C:/Financehub/extracted_pohon_from_bak.txt", "w", encoding="utf-8") as out:
        out.write(block)
    print("Found and extracted from .bak! Length:", len(block))
else:
    print("Not found in .bak")
