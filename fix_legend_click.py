import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'filter: function\(item, chart\) \{ return !item\.text\.includes\(\'\(Total\)\'\); \}\s*\}\s*\},'
repl = """filter: function(item, chart) { return !item.text.includes('(Total)'); }
                      },
                      onClick: function(e, legendItem, legend) {
                          const index = legendItem.datasetIndex;
                          const ci = legend.chart;
                          const isHidden = ci.getDatasetMeta(index).hidden;
                          
                          // Toggle the clicked dataset
                          ci.getDatasetMeta(index).hidden = isHidden === null ? true : !isHidden;
                          
                          // Find and toggle the corresponding (Total) dataset
                          ci.data.datasets.forEach(function(ds, i) {
                              if (ds.label === legendItem.text + " (Total)") {
                                  ci.getDatasetMeta(i).hidden = isHidden === null ? true : !isHidden;
                              }
                          });
                          ci.update();
                      }
                  },"""

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Added custom legend onClick to BudgetVsRealisasiChart!")
