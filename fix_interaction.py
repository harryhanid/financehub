import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

start_str = ",\n      interaction: { mode: 'index', intersect: false },"
end_str = "    }\n  });\n}"

start_idx = content.find(start_str)
if start_idx != -1:
    end_idx = content.find(end_str, start_idx)
    if end_idx != -1:
        content = content[:start_idx] + "\n" + content[end_idx + len(end_str):]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Hanging block removed!")
    else:
        print("Could not find end.")
else:
    print("Could not find start.")
