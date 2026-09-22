import sys
import re

def patch_sahabat_js():
    with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'r', encoding='utf-8') as f:
        content = f.read()

    new_func = """function setfRenderBudgetVsRealisasiChart(canvasId, labels, budgets, realisasis) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  
  const budgetColor = "rgba(148, 163, 184, 0.8)"; // Slate 400
  const realisasiColor = "rgba(59, 130, 246, 0.9)"; // Blue 500
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Budget",
          data: budgets,
          backgroundColor: budgetColor,
          borderRadius: 4,
        },
        {
          label: "Realisasi",
          data: realisasis,
          backgroundColor: realisasiColor,
          borderRadius: 4,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      onClick: function (evt, elements) {
        if (!elements.length) return;
        let lbl = labels[elements[0].index];
        if (lbl !== "Total") {
            setfSetKategoriDrilldown(lbl);
        }
      },
      plugins: {
        legend: { position: "top", labels: { color: textColor } },
        datalabels: {
          display: false // hide data labels because bars can be crowded
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.dataset.label + ": " + formatRupiahShort(context.raw);
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
            callback: function(value) { return formatRupiahShort(value); }
          }
        },
        x: {
          grid: { display: false },
          ticks: { color: textColor }
        }
      }
    }
  });
}
"""

    if "function setfRenderBudgetVsRealisasiChart" not in content:
        content = content.replace("function setfRenderDoughnutChart", new_func + "\nfunction setfRenderDoughnutChart")

    call_old = """      setfRenderDoughnutChart("chart-kategori",
        data.kategori.map(function (k) { return k.cat1; }),
        data.kategori.map(function (k) { return k.realisasi; }),
        data.kategori.map(function (k) { return setfColorForCategory(k.cat1); }));"""
        
    call_new = """      let labels = data.kategori.map(function (k) { return k.cat1 || "Tanpa Kategori"; });
      let budgets = data.kategori.map(function (k) { return k.budget; });
      let realisasis = data.kategori.map(function (k) { return k.realisasi; });
      
      let totalBudget = budgets.reduce((a, b) => a + b, 0);
      let totalRealisasi = realisasis.reduce((a, b) => a + b, 0);
      
      labels.push("Total");
      budgets.push(totalBudget);
      realisasis.push(totalRealisasi);
      
      setfRenderBudgetVsRealisasiChart("chart-kategori", labels, budgets, realisasis);"""
      
    content = content.replace(call_old, call_new)

    with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patched sahabat_etf.js successfully!")

if __name__ == '__main__':
    patch_sahabat_js()
