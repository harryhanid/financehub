file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

import re
# Find the start of the function and the end of the broken part
content = re.sub(r'function setfRenderBudgetVsRealisasiChart[\s\S]*?function setfRenderDoughnutChart', "function setfRenderDoughnutChart", content)

content = re.sub(r'function setfRenderStackedGroupedChart[\s\S]*?function setfRenderSummaryCards', "function setfRenderSummaryCards", content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Removed broken functions!")
