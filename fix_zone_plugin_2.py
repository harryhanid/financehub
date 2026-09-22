import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'data: \{ labels: dual\.labels, datasets: dual\.datasets \},\n\s*plugins: \[ChartDataLabels, setfGroupedSublabelPlugin\],'
repl = """data: { labels: dual.labels, datasets: dual.datasets },
          plugins: [ChartDataLabels, setfGroupedSublabelPlugin, setfTotalZonePlugin],"""

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Added setfTotalZonePlugin to setfRenderBudgetVsRealisasiChart!")
