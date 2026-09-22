import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'function setfRenderBarChart\(canvasId, labels, datasets, onBarClick\) \{[\s\S]*?\}\);'

replacement = """function setfRenderBarChart(canvasId, labels, datasets, onBarClick) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

  const applyTotal = canvasId !== "chart-bulanan";
  let localLabels = labels.slice();
  let localDatasets = [];

  if (applyTotal) {
    localLabels.push("TOTAL");
    datasets.forEach(function(ds) {
      const dsClone = Object.assign({}, ds);
      dsClone.data = ds.data.slice();
      
      let sum = 0;
      dsClone.data.forEach(function(v) { if (typeof v === "number" && !isNaN(v)) sum += v; });
      
      dsClone.data.push(null);
      dsClone.yAxisID = "y";
      localDatasets.push(dsClone);
      
      const shadowClone = Object.assign({}, ds);
      shadowClone.label = ds.label + " (Shadow)";
      shadowClone.data = new Array(localLabels.length - 1).fill(null);
      shadowClone.data.push(sum);
      shadowClone.yAxisID = "y-right";
      localDatasets.push(shadowClone);
    });
  } else {
    datasets.forEach(function(ds) {
      const dsClone = Object.assign({}, ds);
      dsClone.yAxisID = "y";
      localDatasets.push(dsClone);
    });
  }

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const scalesCfg = {
    x: { 
        ticks: {
          color: setfThemeColor("--text-secondary", "#94a3b8"),
          callback: function(val, idx) {
              let lbl = this.getLabelForValue(val);
              if (Array.isArray(lbl)) return lbl.map(function(x) { return "               "; });
              return lbl;
          }
        }, 
        grid: { color: "rgba(148,163,184,0.1)" } 
      },
    y: {
      type: 'linear',
      display: true,
      position: 'left',
      ticks: {
        color: setfThemeColor("--text-secondary", "#94a3b8"),
        callback: function (value) { return setfFmtJutaan(value); },
      },
      grid: { color: "rgba(148,163,184,0.1)" },
    }
  };

  if (applyTotal) {
    scalesCfg['y-right'] = {
      type: 'linear',
      display: true,
      position: 'right',
      title: { 
        display: true, 
        text: 'Skala Total (Juta Rp)', 
        color: setfThemeColor("--text-secondary", "#94a3b8"), 
        font: {weight: 'bold', size: 11} 
      },
      grid: { drawOnChartArea: false },
      ticks: {
        color: setfThemeColor("--text-secondary", "#94a3b8"),
        callback: function (value) { return setfFmtJutaan(value); },
      }
    };
  }

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: localLabels, datasets: localDatasets },
    plugins: [ChartDataLabels, setfGroupedSublabelPlugin],
    options: {
      responsive: true,
      onClick: function (evt, elements) {
        if (!elements.length || !onBarClick) return;
        const clickedIdx = elements[0].index;
        if (applyTotal && clickedIdx === localLabels.length - 1) return;
        onBarClick(clickedIdx);
      },
      plugins: {
        legend: { 
          labels: { 
            color: setfThemeColor("--text-primary", "#e2e8f0"),
            filter: function(item, chart) {
              return !item.text.includes('(Shadow)');
            }
          } 
        },
        datalabels: {
          anchor: "end",
          align: "top",
          color: setfThemeColor("--text-primary", "#e2e8f0"),
          font: { size: 10, weight: "600" },
          formatter: setfDatalabelFormatter,
        },
      },
      scales: scalesCfg,
    },
  });"""

content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated setfRenderBarChart")
