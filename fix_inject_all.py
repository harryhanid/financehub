file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

import re

# Remove any existing versions of the functions we are about to inject
for func in ["function setfRenderBudgetVsRealisasiChart", "function setfRenderStackedGroupedChart", "function setfInjectDualYAxis", "const setfTotalZonePlugin", "const setfStackTotalPlugin"]:
    if "function" in func:
        content = re.sub(func + r'\b[\s\S]*?\n\}\n', '', content)
    else:
        content = re.sub(func + r'\b[\s\S]*?;\n', '', content)

plugins = """
const setfTotalZonePlugin = {
  id: 'totalZone',
  beforeDraw: function(chart) {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const ctx = chart.ctx;
    const xAxis = chart.scales.x;
    const yAxisRight = chart.scales['y-right'];
    if (!xAxis || !yAxisRight) return;
    
    let totalIndex = -1;
    xAxis.getTicks().forEach((tick, i) => {
       if (tick.label === "TOTAL") totalIndex = i;
    });
    if (totalIndex === -1) return;
    
    const leftX = totalIndex === 0 ? xAxis.left : (xAxis.getPixelForTick(totalIndex - 1) + xAxis.getPixelForTick(totalIndex)) / 2;
    const rightX = xAxis.right;
    
    const topY = chart.chartArea.top;
    const bottomY = chart.chartArea.bottom;
    
    ctx.save();
    ctx.beginPath();
    ctx.setLineDash([5, 5]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)";
    ctx.fillStyle = isDark ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.02)";
    ctx.rect(leftX, topY, rightX - leftX, bottomY - topY);
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }
};

const setfStackTotalPlugin = {
  id: 'customLabels',
  afterDatasetsDraw: function(chart) {
    const ctx = chart.ctx;
    ctx.save();
    
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    ctx.font = 'bold 10px sans-serif';
    ctx.fillStyle = isDark ? "#e2e8f0" : "#475569";
    ctx.textAlign = 'center';
    
    const metaMap = {};
    chart.data.datasets.forEach(function(dataset, i) {
      const meta = chart.getDatasetMeta(i);
      if (!meta.hidden && !dataset.label.includes("(Shadow)")) {
         const stackId = meta.stack || 'default';
         if (!metaMap[stackId]) metaMap[stackId] = [];
         metaMap[stackId].push({ index: i, meta: meta, data: dataset.data });
      }
    });

    const numDataPoints = chart.data.labels.length;
    const yBaseline = chart.scales.y.getPixelForValue(0);

    for (let stackId in metaMap) {
      const layers = metaMap[stackId];
      for (let j = 0; j < numDataPoints; j++) {
        let sum = 0;
        let lastValidMeta = null;
        let anyMeta = null; 
        
        for (let l = 0; l < layers.length; l++) {
           const val = layers[l].data[j];
           if (layers[l].meta.data[j]) anyMeta = layers[l].meta.data[j];
           if (val) {
              sum += val;
              lastValidMeta = layers[l].meta.data[j];
           }
        }
        
        if (sum > 0 && lastValidMeta) {
           ctx.textBaseline = 'bottom';
           const xPos = lastValidMeta.x;
           const yPos = chart.scales.y.getPixelForValue(sum);
           ctx.fillText(setfFmtJutaan(sum), xPos, yPos - 5);
        }
        
        if (anyMeta && (stackId === "StackBudget" || stackId === "StackRealisasi")) {
           ctx.textBaseline = 'top';
           ctx.font = '9px sans-serif';
           ctx.fillStyle = isDark ? "#94a3b8" : "#64748b";
           let lbl = stackId === "StackBudget" ? "B" : "R";
           if (chart.canvas.id.includes("tahunan")) lbl = stackId === "StackBudget" ? "Budget" : "Realisasi";
           ctx.fillText(lbl, anyMeta.x, yBaseline + 14);
        }
      }
    }
    ctx.restore();
  }
};
"""

bvr_body = """
function setfRenderBudgetVsRealisasiChart(canvasId, labels, budgets, realisasis) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

    let rawDatasets = [];
    labels.forEach(function(lbl, idx) {
        let b = budgets[idx] || 0;
        let r = realisasis[idx] || 0;
        let color = setfColorForCategory(lbl);
        if (canvasId.includes("pillar")) {
            if (lbl === "AGRI") color = "#10b981";
            else if (lbl === "APP") color = "#3b82f6";
            else if (lbl === "FINANCE") color = "#f59e0b";
            else if (lbl === "SETF") color = "#8b5cf6";
            else color = "#64748b";
        }
        
        rawDatasets.push({
            label: lbl + " (Budget)",
            data: [b],
            backgroundColor: color,
            borderColor: setfShadeColor(color, -20),
            borderWidth: 1,
            stack: "StackBudget",
            barPercentage: 0.8,
            categoryPercentage: 0.8
        });
        
        rawDatasets.push({
            label: lbl + " (Actual)",
            data: [r],
            backgroundColor: typeof pattern !== 'undefined' ? pattern.draw('diagonal-right-left', color) : color,
            borderColor: setfShadeColor(color, -20),
            borderWidth: 1,
            stack: "StackRealisasi",
            barPercentage: 0.8,
            categoryPercentage: 0.8
        });
    });

    let scalesCfg = {
        x: {
            stacked: true,
            ticks: { color: textColor, padding: 20 },
            grid: { color: gridColor, display: false }
        },
        y: {
            type: 'linear', display: true, position: 'left',
            stacked: true,
            ticks: { color: textColor, callback: function (value) { return setfFmtJutaan(value); } },
            grid: { color: gridColor }
        }
    };

    const dual = setfInjectDualYAxis(['Total'], rawDatasets, scalesCfg);
    if (dual.scales['y-right']) dual.scales['y-right'].stacked = true;

    setfCharts[canvasId] = new Chart(ctx, {
        type: "bar",
        data: { labels: dual.labels, datasets: dual.datasets },
        plugins: [ChartDataLabels, setfStackTotalPlugin, setfTotalZonePlugin],
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
                        filter: function(item, chart) { return !item.text.includes('(Shadow)'); }
                    }
                },
                datalabels: { display: false }
            },
            scales: dual.scales
        }
    });
}
"""

sg_body = """
function setfRenderStackedGroupedChart(canvasId, years, dataList, mode) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

    let activeItems = dataList;
    let rawDatasets = [];
    let showBudget = (mode === "all" || mode === "budget" || !mode);
    let showActual = (mode === "all" || mode === "actual" || mode === "realisasi" || !mode);

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
               backgroundColor: color,
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
            ticks: { color: textColor, padding: 20 },
            grid: { color: gridColor, display: false }
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
        plugins: [ChartDataLabels, setfStackTotalPlugin, setfTotalZonePlugin],
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
                datalabels: { display: false }
            },
            scales: dual.scales
        }
    });
}
"""

dual_y_body = """
function setfInjectDualYAxis(labels, rawDatasets, baseScales) {
    if (!labels || !labels.length) return { labels: [], datasets: rawDatasets, scales: baseScales };
    let newLabels = [...labels, "TOTAL"];
    let newDatasets = [];
    
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";
    
    let totalBgt = 0;
    let totalAct = 0;
    
    rawDatasets.forEach(ds => {
        let newData = [...ds.data, 0]; 
        let shadowData = new Array(labels.length + 1).fill(0);
        
        if (ds.stack === "StackBudget") {
            const sum = ds.data.reduce((a, b) => a + (b||0), 0);
            shadowData[labels.length] = sum;
            totalBgt += sum;
        } else if (ds.stack === "StackRealisasi") {
            const sum = ds.data.reduce((a, b) => a + (b||0), 0);
            shadowData[labels.length] = sum;
            totalAct += sum;
        }
        
        ds.data = newData;
        ds.yAxisID = 'y';
        newDatasets.push(ds);
        
        let shadow = Object.assign({}, ds);
        shadow.data = shadowData;
        shadow.yAxisID = 'y-right';
        shadow.label = ds.label + " (Shadow)";
        shadow.backgroundColor = "transparent";
        shadow.borderColor = "transparent";
        if (typeof pattern !== 'undefined' && shadow.backgroundColor && shadow.backgroundColor.draw) {
            shadow.backgroundColor = "transparent"; 
        }
        newDatasets.push(shadow);
    });
    
    let yRight = {
        type: 'linear', display: true, position: 'right',
        stacked: true,
        ticks: { color: textColor, callback: function (value) { return setfFmtJutaan(value); } },
        grid: { drawOnChartArea: false, color: gridColor }
    };
    
    let maxLeft = Math.max(totalBgt, totalAct) * 1.1;
    baseScales['y'].max = maxLeft;
    yRight.max = maxLeft;
    
    baseScales['y-right'] = yRight;
    
    return { labels: newLabels, datasets: newDatasets, scales: baseScales };
}
"""

content = content + "\n\n" + plugins + bvr_body + sg_body + dual_y_body

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Injected all final fixes!")
