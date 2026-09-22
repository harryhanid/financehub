import sys
import re

def patch_js():
    with open(r'C:\Financehub\app\static\js\dashboard_beasiswa.js', 'r', encoding='utf-8') as f:
        content = f.read()

    new_func = """function dashRenderBudgetVsRealisasiChart(canvasId, labels, budgets, realisasis) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (dashCharts[canvasId]) dashCharts[canvasId].destroy();
  
  const budgetColor = "rgba(148, 163, 184, 0.8)"; // Slate 400
  const realisasiColor = "rgba(59, 130, 246, 0.9)"; // Blue 500
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#e2e8f0" : "#475569";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

  dashCharts[canvasId] = new Chart(ctx, {
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

    if "function dashRenderBudgetVsRealisasiChart" not in content:
        # insert after dashRenderDoughnutChart
        content = content.replace("function dashRenderDoughnutChart", new_func + "\nfunction dashRenderDoughnutChart")

    call_old = """      dashRenderDoughnutChart("dash-chart-kategori",
        data.data.kategori.map(function (k) { return k.cat1; }),
        data.data.kategori.map(function (k) { return k.realisasi; }),
        data.data.kategori.map(function (k) { return dashColorForCategory(k.cat1); }));"""
        
    call_new = """      let labels = data.data.kategori.map(function (k) { return k.cat1 || "Tanpa Kategori"; });
      let budgets = data.data.kategori.map(function (k) { return k.budget; });
      let realisasis = data.data.kategori.map(function (k) { return k.realisasi; });
      
      let totalBudget = budgets.reduce((a, b) => a + b, 0);
      let totalRealisasi = realisasis.reduce((a, b) => a + b, 0);
      
      labels.push("Total");
      budgets.push(totalBudget);
      realisasis.push(totalRealisasi);
      
      dashRenderBudgetVsRealisasiChart("dash-chart-kategori", labels, budgets, realisasis);"""
      
    content = content.replace(call_old, call_new)

    with open(r'C:\Financehub\app\static\js\dashboard_beasiswa.js', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patched dashboard_beasiswa.js successfully!")

if __name__ == '__main__':
    patch_js()
