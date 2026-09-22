import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'legend: \{\s*display: true,\s*position: \'top\',\s*align: \'start\',\s*labels: \{ color: textColor, boxWidth: 12 \}\s*\},'

replacement = """legend: { 
                   display: true,
                   position: 'top',
                   align: 'start',
                   labels: { 
                       color: textColor, boxWidth: 12,
                       generateLabels: function(chart) {
                           const original = Chart.defaults.plugins.legend.labels.generateLabels(chart);
                           let unique = [];
                           let seen = new Set();
                           original.forEach(l => {
                               let text = l.text.replace(" (Budget)", "").replace(" (Realisasi)", "");
                               if (!seen.has(text)) {
                                   seen.add(text);
                                   l.text = text;
                                   unique.push(l);
                               }
                           });
                           return unique;
                       }
                   },
                   onClick: function(e, legendItem, legend) {
                       const chart = legend.chart;
                       const datasets = chart.data.datasets;
                       let isCurrentlyHidden = null;
                       datasets.forEach((ds, i) => {
                           if (ds.label.startsWith(legendItem.text + " (")) {
                               const meta = chart.getDatasetMeta(i);
                               if (isCurrentlyHidden === null) {
                                   isCurrentlyHidden = meta.hidden;
                               }
                               meta.hidden = isCurrentlyHidden === null ? true : !isCurrentlyHidden;
                           }
                       });
                       chart.update();
                   }
                },"""

content = re.sub(target, replacement, content, count=1, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
