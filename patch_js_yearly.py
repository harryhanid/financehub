import sys
import re

def patch_js():
    with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'r', encoding='utf-8') as f:
        content = f.read()

    old_func = """function setfRenderYearlyChart(yearly) {
  if (!yearly || !yearly.length) {
    if (setfCharts["chart-tahunan"]) { setfCharts["chart-tahunan"].destroy(); delete setfCharts["chart-tahunan"]; }
    return;
  }
  setfRenderBarChart("chart-tahunan", yearly.map(function (y) { return y.tahun; }), [
    { label: "Realisasi", data: yearly.map(function (y) { return y.realisasi; }), backgroundColor: "#10b981" },
  ]);
}"""

    new_func = """function setfRenderStackedGroupedChart(canvasId, labels, dataList) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

  let datasets = [];
  dataList.forEach(function(item) {
    let color = setfColorForCategory(item.name);
    // Budget stack
    datasets.push({
      label: item.name + " (Budget)",
      data: item.budget,
      backgroundColor: color + "66", // faded
      stack: "Budget"
    });
    // Realisasi stack
    datasets.push({
      label: item.name + " (Realisasi)",
      data: item.realisasi,
      backgroundColor: color, // solid
      stack: "Realisasi"
    });
  });

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    plugins: [ChartDataLabels],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 20 } },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: "right", labels: { color: textColor } },
        datalabels: {
          display: function(context) {
             return context.dataset.data[context.dataIndex] > 0; // only show if > 0
          },
          align: 'center',
          anchor: 'center',
          color: isDark ? '#fff' : '#000',
          font: { size: 9 },
          formatter: function(value) {
            return setfFmtJutaan(value);
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.dataset.label + ": " + setfFmtJutaan(context.raw);
            }
          }
        }
      },
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
          ticks: { color: textColor }
        },
        y: {
          stacked: true,
          beginAtZero: true,
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            callback: function(value) { return setfFmtJutaan(value); }
          }
        }
      }
    }
  });
}

function setfRenderYearlyChart(yearly) {
  if (!yearly || !yearly.years || !yearly.years.length) {
    if (setfCharts["chart-tahunan-kategori"]) { setfCharts["chart-tahunan-kategori"].destroy(); delete setfCharts["chart-tahunan-kategori"]; }
    if (setfCharts["chart-tahunan-pillar"]) { setfCharts["chart-tahunan-pillar"].destroy(); delete setfCharts["chart-tahunan-pillar"]; }
    return;
  }
  setfRenderStackedGroupedChart("chart-tahunan-kategori", yearly.years, yearly.kategori);
  setfRenderStackedGroupedChart("chart-tahunan-pillar", yearly.years, yearly.pillar);
}"""

    if old_func in content:
        content = content.replace(old_func, new_func)
        with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched sahabat_etf.js")
    else:
        print("Could not find old_func in sahabat_etf.js")

if __name__ == '__main__':
    patch_js()
