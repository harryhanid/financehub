import re
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_yearly = r'function setfRenderYearlyChart\(yearly\) \{[\s\S]*?\}\]\);\n\s*\}'
new_yearly = """function setfRenderTotalTable(tableId, dataList) {
  const tbody = document.querySelector("#" + tableId + " tbody");
  if (!tbody) return;
  if (!dataList || !dataList.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Belum ada data.</td></tr>';
    return;
  }
  
  let grandBudget = 0;
  let grandRealisasi = 0;
  
  const rows = dataList.map(function(item) {
     const totalBudget = item.budget.reduce((a, b) => a + (b||0), 0);
     const totalRealisasi = item.realisasi.reduce((a, b) => a + (b||0), 0);
     const sisa = totalBudget - totalRealisasi;
     const pctSisa = totalBudget > 0 ? (sisa / totalBudget) * 100 : 0;
     
     grandBudget += totalBudget;
     grandRealisasi += totalRealisasi;
     
     return "<tr>" + 
       "<td>" + item.name + "</td>" +
       "<td class='num-right'>" + setfFmtJutaan(totalBudget) + "</td>" + 
       "<td class='num-right'>" + setfFmtJutaan(totalRealisasi) + "</td>" + 
       setfSisaCell(sisa) + 
       "<td class='num-right'>" + pctSisa.toFixed(1) + "%</td>" + 
       "</tr>";
  }).join("");
  
  const grandSisa = grandBudget - grandRealisasi;
  const grandPct = grandBudget > 0 ? (grandSisa / grandBudget) * 100 : 0;
  const totalRow = "<tr style='font-weight:bold'>" +
    "<td>Total Keseluruhan</td>" +
    "<td class='num-right'>" + setfFmtJutaan(grandBudget) + "</td>" + 
    "<td class='num-right'>" + setfFmtJutaan(grandRealisasi) + "</td>" + 
    setfSisaCell(grandSisa) + 
    "<td class='num-right'>" + grandPct.toFixed(1) + "%</td>" + 
    "</tr>";
    
  tbody.innerHTML = rows + totalRow;
}

function setfRenderYearlyChart(yearly) {
  if (!yearly || !yearly.years || !yearly.years.length) {
    if (setfCharts["chart-tahunan-kategori"]) { setfCharts["chart-tahunan-kategori"].destroy(); delete setfCharts["chart-tahunan-kategori"]; }
    if (setfCharts["chart-tahunan-pillar"]) { setfCharts["chart-tahunan-pillar"].destroy(); delete setfCharts["chart-tahunan-pillar"]; }
    setfRenderTotalTable("setf-tahunan-kategori-table", []);
    setfRenderTotalTable("setf-tahunan-pillar-table", []);
    return;
  }
  setfRenderStackedGroupedChart("chart-tahunan-kategori", yearly.years, yearly.kategori);
  setfRenderStackedGroupedChart("chart-tahunan-pillar", yearly.years, yearly.pillar);
  
  setfRenderTotalTable("setf-tahunan-kategori-table", yearly.kategori);
  setfRenderTotalTable("setf-tahunan-pillar-table", yearly.pillar);
}"""

content = re.sub(target_yearly, new_yearly, content)

bvr_body = """function setfRenderBudgetVsRealisasiChart(canvasId, labels, budgets, realisasis) {
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

sg_body = """function setfRenderStackedGroupedChart(canvasId, years, dataList, mode) {
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

dual_y_body = """function setfInjectDualYAxis(labels, rawDatasets, baseScales) {
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

content = content + "\n\n" + bvr_body + "\n\n" + sg_body + "\n\n" + dual_y_body

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Injected perfectly!")
