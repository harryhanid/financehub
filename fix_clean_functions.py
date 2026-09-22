import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

def replace_function(content, func_name, new_body):
    # Find start of function
    start_idx = content.find(f"function {func_name}(")
    if start_idx == -1:
        return content
    
    # Find the opening brace of the function
    brace_idx = content.find("{", start_idx)
    if brace_idx == -1:
        return content
    
    # Count braces to find the matching closing brace
    brace_count = 1
    idx = brace_idx + 1
    while brace_count > 0 and idx < len(content):
        if content[idx] == '{':
            brace_count += 1
        elif content[idx] == '}':
            brace_count -= 1
        idx += 1
        
    if brace_count == 0:
        # We found the end of the function!
        end_idx = idx
        return content[:start_idx] + new_body + content[end_idx:]
    return content

# 1. Budget vs Realisasi Chart
bvr_body = """function setfRenderBudgetVsRealisasiChart(canvasId, labels, budgets, realisasis, onClickCallback) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

    let rawDatasets = [
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
                        if (lbl.indexOf("Actual") === 0) { 
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
}
"""

content = replace_function(content, "setfRenderBudgetVsRealisasiChart", bvr_body)

# 2. Stacked Grouped Chart
sg_body = """function setfRenderStackedGroupedChart(canvasId, years, dataList, mode) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

    let activeItems = dataList;
    let rawDatasets = [];
    let showBudget = (mode === "all" || mode === "budget");
    let showActual = (mode === "all" || mode === "actual" || mode === "realisasi");

    const shapes = ['dot', 'diagonal-right-left', 'square', 'zigzag', 'triangle', 'weave', 'cross'];
    activeItems.forEach(function(item, idx) {
       let shape = shapes[idx % shapes.length];
       let color = setfColorForCategory(item.originalName || item.name);
       if (canvasId.includes("pillar")) {
           if (item.name === "AGRI") color = "#10b981";
           else if (item.name === "APP") color = "#3b82f6";
           else if (item.name === "FINANCE") color = "#f59e0b";
           else if (item.name === "SETF") color = "#8b5cf6";
           else color = "#64748b";
       }
       
       if (showBudget) {
           rawDatasets.push({
               label: item.name + " (Budget)",
               data: item.budget,
               backgroundColor: typeof pattern !== 'undefined' ? pattern.draw(shape, color) : color,
               borderColor: setfShadeColor(color, -20),
               borderWidth: 1,
               stack: "StackBudget",
               barPercentage: 0.8,
               categoryPercentage: 0.8
           });
       }
       
       if (showActual) {
           rawDatasets.push({
               label: item.name + " (Actual)",
               data: item.realisasi,
               backgroundColor: typeof pattern !== 'undefined' ? pattern.draw(shape, color) : color,
               borderColor: setfShadeColor(color, -20),
               borderWidth: 1,
               stack: "StackRealisasi",
               barPercentage: 0.8,
               categoryPercentage: 0.8
           });
       }
    });

    let scalesCfg = {
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

    const dual = setfInjectDualYAxis(years, rawDatasets, scalesCfg);
    if (dual.scales['y-right']) dual.scales['y-right'].stacked = true;

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
}
"""

content = replace_function(content, "setfRenderStackedGroupedChart", sg_body)

# Wait, if there are ANY OTHER syntax errors (like the hanging plugins: { ... }), 
# since we are just doing replace_function, we might STILL leave hanging code if it wasn't part of a function!
# But all Javascript code is in functions. If there was a trailing } hanging outside, the previous script might have caused it.
# Let's fix ANY floating `      },    },  });},      plugins: {` by regexing it out.
junk = r'\},[\s\n]*\},[\s\n]*\}\);[\s\n]*\},[\s\n]*plugins: \{[\s\S]*?x: \{[\s\n]*grid: \{ display: false \},[\s\n]*ticks: \{ color: textColor \}[\s\n]*\}[\s\n]*\}[\s\n]*\}[\s\n]*\}\);[\s\n]*\}'
content = re.sub(junk, '', content)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated successfully")
