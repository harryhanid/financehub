file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

start_str = "  const rows = kategoriRows.map(function (k) {"
end_str = "  tbody.innerHTML = rows + totalRow;\n"

start_idx = content.find(start_str)
if start_idx != -1:
    end_idx = content.find(end_str, start_idx)
    if end_idx != -1:
        content = content[:start_idx] + content[end_idx + len(end_str):]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Dangling kategoriRows block deleted!")
    else:
        print("Could not find end of block.")
else:
    print("Could not find start of block.")
