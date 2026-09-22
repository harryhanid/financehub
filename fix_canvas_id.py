import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

junk = r'[\s\n]*setfCharts\[canvasId\] = new Chart\(ctx, \{[\s\S]*?type: "bar",[\s\S]*?labels: xLabels[\s\S]*?plugins: \[ChartDataLabels, customKeluargaLabelsPlugin\],[\s\S]*?\}\);\n'

match = re.search(junk, content)
if match:
    print("Found floating block! Removing...")
    content = content[:match.start()] + "\n" + content[match.end():]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
else:
    print("Could not find floating block.")
