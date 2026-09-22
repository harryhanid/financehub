import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Just replace \' with ' in the setfLaporan block
def fix_func(content, func_name):
    start = content.find(f"function {func_name}")
    if start == -1: return content
    end = content.find("}", start) + 1
    old_body = content[start:end]
    new_body = old_body.replace("\\'", "'")
    return content[:start] + new_body + content[end:]

content = fix_func(content, "setfLaporanHeaderRow")
content = fix_func(content, "setfLaporanMetricsCells")
# Wait, setfRenderLaporanPillarBreakdown also has it?
content = fix_func(content, "setfRenderLaporanPillarBreakdown")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed escaping!")
