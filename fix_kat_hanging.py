import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# The dangling block starts right after the NEW setfRenderKategoriTable
# It looks like:
#   const rows = kategoriRows.map(function (k) {
# ...
#   tbody.innerHTML = rows + totalRow;
# }

junk_regex = r'[\s\n]*const rows = kategoriRows\.map\(function \(k\) \{[\s\S]*?tbody\.innerHTML = rows \+ totalRow;\n\}'

match = re.search(junk_regex, content)
if match:
    print("Found hanging block for Kategori Table! Removing...")
    content = content[:match.start()] + "\n" + content[match.end():]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
else:
    print("Could not find hanging block.")
