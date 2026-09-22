import os
import re

path = r'C:\Financehub\app\static\js\sahabat_etf.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix trendTotalBox styling
content = content.replace('ctx.strokeStyle = setfThemeColor("--border-color", "#cbd5e1");', 'ctx.strokeStyle = "rgba(255, 205, 86, 1)";')

# The onClick function to inject
onclick_str = """
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
            },"""

# Inject onClick right after the filter functions in the legends.
# Using regex to find the end of the filter function in the legend labels config.
# The filter usually ends with `}\n          }` (closing the labels block). We will just insert it after the `filter: function(...) { ... }` block.

pattern1 = r'(filter:\s*function\([^)]*\)\s*\{[^}]*\}\n)'
content = re.sub(pattern1, r'\1' + onclick_str, content)

# But wait, in yearly and keluarga charts, the filter function is:
# filter: function(item, data) {
#    const ds = data.datasets[item.datasetIndex];
#    return !ds.hiddenLegend;
# }
pattern2 = r'(filter:\s*function\(item,\s*data\)\s*\{\s*const\s*ds\s*=\s*data\.datasets\[item\.datasetIndex\];\s*return\s*!ds\.hiddenLegend;\s*\})'
content = re.sub(pattern2, r'\1' + onclick_str, content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Injected onClick!")
