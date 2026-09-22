import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

helper = """
function setfInjectDualYAxis(labels, datasets, scalesCfg) {
  let localLabels = labels.slice();
  localLabels.push("TOTAL");
  let newDatasets = [];

  datasets.forEach(function(ds) {
    const dsClone = Object.assign({}, ds);
    dsClone.data = ds.data.slice();
    let sum = 0;
    dsClone.data.forEach(function(v) { if (typeof v === "number" && !isNaN(v)) sum += v; });
    dsClone.data.push(null);
    dsClone.yAxisID = "y";
    newDatasets.push(dsClone);
  });

  datasets.forEach(function(ds) {
    let sum = 0;
    ds.data.forEach(function(v) { if (typeof v === "number" && !isNaN(v)) sum += v; });
    const shadowClone = Object.assign({}, ds);
    shadowClone.label = ds.label + " (Shadow)";
    shadowClone.data = new Array(localLabels.length - 1).fill(null);
    shadowClone.data.push(sum);
    shadowClone.yAxisID = "y-right";
    newDatasets.push(shadowClone);
  });

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#94a3b8" : "#64748b";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

  if (!scalesCfg.y) {
    scalesCfg.y = {
        type: 'linear', display: true, position: 'left',
        ticks: { color: textColor, callback: function (v) { return setfFmtJutaan(v); } },
        grid: { color: gridColor }
    };
  }
  
  scalesCfg['y-right'] = {
      type: 'linear', display: true, position: 'right',
      title: { display: true, text: 'Skala Total (Juta Rp)', color: textColor, font: {weight: 'bold'} },
      grid: { drawOnChartArea: false },
      ticks: { color: textColor, callback: function (v) { return setfFmtJutaan(v); } }
  };

  return { labels: localLabels, datasets: newDatasets, scales: scalesCfg };
}
"""

if "function setfInjectDualYAxis" not in content:
    content = content.replace("function setfRenderBudgetVsRealisasiChart", helper + "\nfunction setfRenderBudgetVsRealisasiChart")

# We will modify both functions to use this new helper.
import sys

def modify_budget_vs_actual():
    global content
    target = r'const datasets = \[\s*\{\s*label: "Budget",[\s\S]*?y: \{\s*ticks: \{\s*color: textColor,\s*callback: function \(value\) \{ return setfFmtJutaan\(value\); \}\s*\},\s*grid: \{ color: gridColor \}\s*\}\s*\}\s*\}\s*\}\);\s*\}'
    
    repl = """let rawDatasets = [
        {
            label: "Budget",
            data: budgets,
            backgroundColor: "#cbd5e1",
            borderColor: "#94a3b8",
            borderWidth: 1,
            barPercentage: 0.8,
            categoryPercentage: 0.9,
        },
        {
            label: "Actual",
            data: realisasis,
            backgroundColor: "#3b82f6",
            borderColor: "#2563eb",
            borderWidth: 1,
            barPercentage: 0.8,
            categoryPercentage: 0.9,
        }
    ];

    let scalesCfg = {
        x: {
            ticks: { 
                color: textColor, 
                callback: function(val, idx) {
                    let lbl = this.getLabelForValue(val);
                    if (Array.isArray(lbl)) return lbl.map(function(x) { return "               "; });
                    return lbl;
                }
            },
            grid: { color: gridColor }
        },
        y: {
            type: 'linear', display: true, position: 'left',
            ticks: { color: textColor, callback: function (value) { return setfFmtJutaan(value); } },
            grid: { color: gridColor }
        }
    };

    const dual = setfInjectDualYAxis(labels, rawDatasets, scalesCfg);

    setfCharts[canvasId] = new Chart(ctx, {
        type: "bar",
        data: { labels: dual.labels, datasets: dual.datasets },
        plugins: [ChartDataLabels, setfGroupedSublabelPlugin],
        options: {
            responsive: true,
            onClick: function (evt, elements) {
                if (!elements.length || !onClickCallback) return;
                const clickedIdx = elements[0].index;
                if (clickedIdx === dual.labels.length - 1) return; // Prevent clicking TOTAL
                onClickCallback(dual.labels[clickedIdx]);
            },
            layout: { padding: { top: 20, bottom: 25 } },
            plugins: {
                legend: { 
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: { 
                        color: textColor, boxWidth: 12,
                        filter: function(item, chart) { return !item.text.includes('(Shadow)'); }
                    }
                },
                datalabels: {
                    anchor: "end",
                    align: "top",
                    color: textColor,
                    font: { size: 10, weight: "bold" },
                    textAlign: "center",
                    formatter: function(val, context) {
                        if (val <= 0) return "";
                        const lbl = context.dataset.label || "";
                        if (lbl.indexOf("Actual") === 0) { // Actual or Actual (Shadow)
                            const bgtIdx = context.datasetIndex === 1 ? 0 : 2; // Original logic: Budget is 0, Actual is 1. If shadow, Budget shadow is 2, Actual shadow is 3
                            // Wait, if it's Actual, context.datasetIndex is 1. Its budget is 0.
                            // If it's Actual (Shadow), context.datasetIndex is 3. Its budget is 2.
                            const correspondingBgtIdx = context.datasetIndex - 1; 
                            const b = context.chart.data.datasets[correspondingBgtIdx].data[context.dataIndex];
                            if (b > 0) {
                                const pct = (val / b * 100).toFixed(1);
                                return [setfFmtJutaan(val), "(" + pct + "%)"];
                            }
                        }
                        return setfFmtJutaan(val);
                    }
                }
            },
            scales: dual.scales
        }
    });
}"""
    content = re.sub(target, repl, content)

def modify_stacked_grouped():
    global content
    target = r'setfCharts\[canvasId\] = new Chart\(ctx, \{\s*type: "bar",[\s\S]*?y: \{\s*stacked: true,\s*ticks: \{\s*color: textColor,\s*callback: function \(value\) \{ return setfFmtJutaan\(value\); \}\s*\},\s*grid: \{ color: gridColor \}\s*\}\s*\}\s*\}\s*\}\);\s*\}'
    
    repl = """let scalesCfg = {
        x: {
            stacked: true,
            ticks: { color: textColor },
            grid: { color: gridColor }
        },
        y: {
            type: 'linear', display: true, position: 'left',
            stacked: true,
            ticks: { color: textColor, callback: function (value) { return setfFmtJutaan(value); } },
            grid: { color: gridColor }
        }
    };

    const dual = setfInjectDualYAxis(years, datasets, scalesCfg);
    
    // Ensure stacked is true for y-right as well
    dual.scales['y-right'].stacked = true;

    setfCharts[canvasId] = new Chart(ctx, {
        type: "bar",
        data: { labels: dual.labels, datasets: dual.datasets },
        plugins: [ChartDataLabels, setfStackTotalPlugin],
        options: {
            responsive: true,
            layout: { padding: { top: 20, bottom: 25 } },
            plugins: {
                legend: { 
                   display: true,
                   position: 'top',
                   align: 'end',
                   labels: { 
                       color: textColor, boxWidth: 12,
                       generateLabels: function(chart) {
                           const original = Chart.defaults.plugins.legend.labels.generateLabels(chart);
                           let unique = [];
                           let seen = new Set();
                           original.forEach(function(item) {
                               if (item.text.includes('(Shadow)')) return;
                               const baseName = item.text.replace(" (Budget)", "").replace(" (Actual)", "");
                               if (!seen.has(baseName)) {
                                   seen.add(baseName);
                                   let newItem = Object.assign({}, item);
                                   newItem.text = baseName;
                                   newItem.datasetIndex = item.datasetIndex;
                                   unique.push(newItem);
                               }
                           });
                           return unique;
                       }
                   },
                   onClick: function(e, legendItem, legend) {
                       const index = legendItem.datasetIndex;
                       const ci = legend.chart;
                       const baseName = legendItem.text;
                       ci.data.datasets.forEach(function(ds, i) {
                           const dsBase = ds.label.replace(" (Budget)", "").replace(" (Actual)", "").replace(" (Shadow)", "");
                           if (dsBase === baseName) {
                               const meta = ci.getDatasetMeta(i);
                               meta.hidden = meta.hidden === null ? !ci.data.datasets[i].hidden : null;
                           }
                       });
                       ci.update();
                   }
                },
                datalabels: {
                    display: function(context) {
                        return context.dataset.data[context.dataIndex] > 0;
                    },
                    color: "white",
                    font: { size: 9, weight: "bold" },
                    formatter: function(val) { return setfFmtJutaan(val); }
                }
            },
            scales: dual.scales
        }
    });
}"""
    content = re.sub(target, repl, content)


modify_budget_vs_actual()
modify_stacked_grouped()

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated successfully")
