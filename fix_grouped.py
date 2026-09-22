import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

grouped_chart = """
const setfGroupedSublabelPlugin = {
    id: 'groupedSublabel',
    afterDraw: function(chart) {
      const ctx = chart.ctx;
      ctx.save();
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      ctx.textBaseline = 'top';
      ctx.font = '10px sans-serif';
      ctx.fillStyle = isDark ? "#94a3b8" : "#64748b";
      ctx.textAlign = 'center';
      
      const yBaseline = chart.scales.y.getPixelForValue(0);
      
      chart.data.datasets.forEach(function(dataset, i) {
        const meta = chart.getDatasetMeta(i);
        if (!meta.hidden) {
            let lbl = "";
            if (dataset.label === "Budget") lbl = "Bgt";
            if (dataset.label === "Realisasi" || dataset.label === "Actual") lbl = "Act";
            if (!lbl) return;
            
            for (let j = 0; j < meta.data.length; j++) {
                if (meta.data[j]) {
                    ctx.fillText(lbl, meta.data[j].x, yBaseline + 10);
                }
            }
        }
      });
      ctx.restore();
    }
};

function setfRenderBudgetVsRealisasiChart(canvasId, labels, budgets, realisasis) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }
  
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

  const budgetColors = labels.map(l => l === "Total" ? (isDark ? "#475569" : "#cbd5e1") : setfColorForCategory(l) + "66");
  const realisasiColors = labels.map(l => l === "Total" ? (isDark ? "#3b82f6" : "#3b82f6") : setfColorForCategory(l));

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Budget",
          data: budgets,
          backgroundColor: budgetColors,
          borderRadius: 4,
          categoryPercentage: 0.8,
          barPercentage: 0.9
        },
        {
          label: "Realisasi",
          data: realisasis,
          backgroundColor: realisasiColors,
          borderRadius: 4,
          categoryPercentage: 0.8,
          barPercentage: 0.9
        }
      ]
    },
    plugins: [ChartDataLabels, setfTotalZonePlugin, setfGroupedSublabelPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 35, bottom: 20 } },
      interaction: {
        mode: 'index',
        intersect: false,
      },
      onClick: function (evt, elements) {
        if (!elements.length) return;
        let lbl = labels[elements[0].index];
        if (lbl !== "Total" && canvasId === "chart-kategori") {
            if (typeof setfSetKategoriDrilldown !== 'undefined') setfSetKategoriDrilldown(lbl);
        }
      },
      plugins: {
        legend: { position: "top", labels: { color: textColor } },
        datalabels: {
          display: true,
          align: 'end',
          anchor: 'end',
          color: textColor,
          font: { size: 10, weight: '500' },
          formatter: function(value) {
            return value ? setfFmtJutaan(value) : "";
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
        y: {
          beginAtZero: true,
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            callback: function(value) { return setfFmtJutaan(value); }
          }
        },
        x: {
          grid: { display: false },
          ticks: { 
            color: textColor,
            padding: 25 
          }
        }
      }
    }
  });
}
"""

target = r'function setfRenderBudgetVsRealisasiChart\(canvasId, labels, budgets, realisasis\) \{[\s\S]*?(?=function setfRenderStackedGroupedChart)'

content = re.sub(target, grouped_chart, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Restored grouped BudgetVsRealisasiChart with sublabels!")
