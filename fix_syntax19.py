import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# I will just replace `\'` with `'` inside these functions!
target_funcs = ["function setfLaporanHeaderRow", "function setfLaporanMetricsCells", "function setfLaporanPeriodeText", "function setfLaporanNamaRow", "function setfLaporanLabelRow"]

for tf in target_funcs:
    start_idx = content.find(tf)
    if start_idx != -1:
        end_idx = content.find("}", start_idx)
        sub = content[start_idx:end_idx+1]
        sub = sub.replace("\\'", "'")
        content = content[:start_idx] + sub + content[end_idx+1:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed escaping quotes!")
