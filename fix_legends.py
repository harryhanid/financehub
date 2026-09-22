import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix setfRenderStackedGroupedChart generateLabels
content = content.replace("if (item.text.includes('(Shadow)')) return;", "if (item.text.includes('(Total)')) return;")
content = content.replace('const baseName = item.text.replace(" (Budget)", "").replace(" (Actual)", "");', 'const baseName = item.text.replace(" (Budget)", "").replace(" (Actual)", "").replace(" (Total)", "");')

# Fix setfRenderStackedGroupedChart legend onClick
content = content.replace('const dsBase = ds.label.replace(" (Budget)", "").replace(" (Actual)", "").replace(" (Shadow)", "");', 'const dsBase = ds.label.replace(" (Budget)", "").replace(" (Actual)", "").replace(" (Total)", "");')

# Fix setfRenderBudgetVsRealisasiChart legend filter
content = content.replace("filter: function(item, chart) { return !item.text.includes('(Shadow)'); }", "filter: function(item, chart) { return !item.text.includes('(Total)'); }")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed legends!")
