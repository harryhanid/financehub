import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

start_idx = content.find("function setfLaporanHeaderRow(reportYear)")
end_idx = content.find("function setfLoadLaporan()")

if start_idx != -1 and end_idx != -1:
    sub = content[start_idx:end_idx]
    sub = sub.replace("\\'", "'")
    content = content[:start_idx] + sub + content[end_idx:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed escaping quotes block!")
else:
    print("Not found")
