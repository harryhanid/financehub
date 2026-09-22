import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'\.then\(function \(data\) \{\s*const xLabels = data\.families.*?setfRenderStackedGroupedChart\("chart-keluarga", xLabels, stackData, "all"\);\s*setfRenderFamilyTable\(data\.families\);'
replacement = """.then(function (data) {
        window._setfLastKeluargaData = data.families;
        setfRenderKeluargaChart(data.families);
        setfRenderFamilyTable(data.families);"""
        
content = re.sub(target, replacement, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
