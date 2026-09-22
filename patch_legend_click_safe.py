import os
import re

path = r'C:\Financehub\app\static\js\sahabat_etf.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix trendTotalBox styling
content = content.replace('ctx.strokeStyle = setfThemeColor("--border-color", "#cbd5e1");', 'ctx.strokeStyle = "rgba(255, 205, 86, 1)";')

onclick_str = """,
            onClick: function(e, legendItem, legend) {
              const index = legendItem.datasetIndex;
              const ci = legend.chart;
              const isVisible = ci.isDatasetVisible(index);
              ci.setDatasetVisibility(index, !isVisible);
              
              const baseLabel = ci.data.datasets[index].label;
              let targetLabel = "";
              if (baseLabel === "Budget") targetLabel = "Budget (Total)";
              else if (baseLabel === "Actual") targetLabel = "Actual (Total)";
              else if (baseLabel.endsWith(" (Act)")) targetLabel = baseLabel.replace(" (Act)", " (ActTot)");
              else targetLabel = baseLabel + " (BgtTot)";

              ci.data.datasets.forEach((ds, i) => {
                if (ds.label === targetLabel) {
                  ci.setDatasetVisibility(i, !isVisible);
                }
              });
              ci.update();
            }"""

# Inject onClick safely
# For main dashboard and trend chart
content = content.replace(
    "return !item.text.includes('(Total)');\n            }",
    "return !item.text.includes('(Total)');\n            }" + onclick_str
)

# For yearly and keluarga charts
content = content.replace(
    "return !ds.hiddenLegend;\n             }",
    "return !ds.hiddenLegend;\n             }" + onclick_str
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Injected onClick safely!")
