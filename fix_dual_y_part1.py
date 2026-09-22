import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

def inject_dual_y(match):
    # This function will replace the `datasets = [...]` and `setfCharts[...] = new Chart(...)` block
    # We will pass the text up to `data: { labels: ...` and modify it.
    pass

# We will just write a javascript function `setfInjectDualYAxis(labels, datasets, scales)` and call it inside BOTH functions before `new Chart`!

helper = """
function setfInjectDualYAxis(labels, datasets, scales) {
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

  // Push shadows after so datalabel index logic (0=Bgt, 1=Act) is preserved for normal bars!
  // Wait, if shadows are at the end, dataset index 0 and 1 are still original!
  datasets.forEach(function(ds) {
    const dsClone = Object.assign({}, ds);
    dsClone.data = ds.data.slice();
    let sum = 0;
    dsClone.data.forEach(function(v) { if (typeof v === "number" && !isNaN(v)) sum += v; });
    
    const shadowClone = Object.assign({}, ds);
    shadowClone.label = ds.label + " (Shadow)";
    shadowClone.data = new Array(localLabels.length - 1).fill(null);
    shadowClone.data.push(sum);
    shadowClone.yAxisID = "y-right";
    newDatasets.push(shadowClone);
  });

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  
  if (!scales) scales = {};
  if (!scales.y) {
    scales.y = {
        type: 'linear', display: true, position: 'left',
        ticks: { color: isDark ? "#94a3b8" : "#64748b", callback: function (v) { return setfFmtJutaan(v); } },
        grid: { color: isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)" }
    };
  }
  
  scales['y-right'] = {
      type: 'linear', display: true, position: 'right',
      title: { display: true, text: 'Skala Total (Juta Rp)', color: isDark ? "#94a3b8" : "#64748b", font: {weight: 'bold'} },
      grid: { drawOnChartArea: false },
      ticks: { color: isDark ? "#94a3b8" : "#64748b", callback: function (v) { return setfFmtJutaan(v); } }
  };

  return { labels: localLabels, datasets: newDatasets, scales: scales };
}
"""

if "function setfInjectDualYAxis" not in content:
    content = content.replace("function setfRenderBudgetVsRealisasiChart", helper + "\nfunction setfRenderBudgetVsRealisasiChart")

# Modify setfRenderBudgetVsRealisasiChart
target1 = r'data: \{ labels: labels, datasets: datasets \},\s*plugins: \[ChartDataLabels, setfGroupedSublabelPlugin\],'
repl1 = """data: (function(){ 
            window._tempDualY = setfInjectDualYAxis(labels, datasets, {}); 
            return { labels: window._tempDualY.labels, datasets: window._tempDualY.datasets }; 
        })(),
        plugins: [ChartDataLabels, setfGroupedSublabelPlugin],"""
content = re.sub(target1, repl1, content)

target1b = r'scales: \{\s*x: \{'
repl1b = """scales: window._tempDualY.scales,
            _dummyX: {
                x: {"""
content = re.sub(target1b, repl1b, content)

# But wait, we need to preserve the X scale from the original!
