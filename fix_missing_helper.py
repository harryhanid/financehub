file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

helper = """
function setfInjectDualYAxis(labels, datasets, scales) {
  let localLabels = labels.slice();
  let newDatasets = [];

  datasets.forEach(function(ds) {
    const dsClone = Object.assign({}, ds);
    dsClone.data = ds.data.slice();
    
    let sum = 0;
    dsClone.data.forEach(function(v) { if (typeof v === "number" && !isNaN(v)) sum += v; });
    
    dsClone.data.push(null);
    newDatasets.push(dsClone);
    
    const shadowDs = Object.assign({}, dsClone);
    shadowDs.data = dsClone.data.map(() => null);
    shadowDs.data[shadowDs.data.length - 1] = sum;
    shadowDs.yAxisID = 'y-right';
    shadowDs.label = dsClone.label + " (Total)";
    
    if (shadowDs.backgroundColor) shadowDs.backgroundColor = shadowDs.backgroundColor;
    
    newDatasets.push(shadowDs);
  });

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  scales['y-right'] = {
    type: 'linear', display: true, position: 'right',
    title: { display: true, text: "Skala Total (Juta Rp)", color: isDark ? "#94a3b8" : "#64748b", font: {size: 10} },
    grid: { drawOnChartArea: false },
    ticks: {
      color: isDark ? "#94a3b8" : "#64748b",
      callback: function(value) { return setfFmtJutaan(value); }
    }
  };

  return { labels: localLabels, datasets: newDatasets, scales: scales };
}
"""

if "function setfInjectDualYAxis" not in content:
    content = content.replace("function setfRenderBudgetVsRealisasiChart", helper + "\nfunction setfRenderBudgetVsRealisasiChart")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Injected setfInjectDualYAxis successfully!")
else:
    print("Already exists.")
