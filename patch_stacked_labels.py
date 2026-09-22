import sys
import re

def patch_js():
    with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'r', encoding='utf-8') as f:
        content = f.read()

    old_func_pattern = re.compile(r'function setfRenderStackedGroupedChart\(canvasId, labels, dataList\).*?\}\s*\}', re.DOTALL)
    
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
      label: item.name,
      data: item.budget,
      backgroundColor: color, // solid
      stack: "Budget"
    });
    // Realisasi stack
    datasets.push({
      label: item.name,
      data: item.realisasi,
      backgroundColor: color, // solid
      stack: "Realisasi"
    });
  });

  const bottomLabelsPlugin = {
    id: 'bottomLabels',
    afterDatasetsDraw: function(chart) {
      const ctx = chart.ctx;
      ctx.save();
      ctx.font = "9px Inter, sans-serif";
      ctx.fillStyle = isDark ? "#94a3b8" : "#64748b"; // muted text color
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      
      const yAxis = chart.scales.y;
      
      chart.data.labels.forEach((_, index) => {
        let metaB = chart.getDatasetMeta(0);
        let metaR = chart.getDatasetMeta(1);
        
        if (metaB.data[index]) {
           let xB = metaB.data[index].x;
           ctx.fillText("Budget", xB, yAxis.bottom + 4);
        }
        if (metaR.data[index]) {
           let xR = metaR.data[index].x;
           ctx.fillText("Realisasi", xR, yAxis.bottom + 4);
        }
      });
      ctx.restore();
    }
  };

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    plugins: [ChartDataLabels, bottomLabelsPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 20 } },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { 
          position: "right", 
          labels: { 
            color: textColor,
            filter: function(item, chart) {
               // Only show the budget dataset (even index) so we get 1 legend item per category
               return item.datasetIndex % 2 === 0;
            }
          } 
        },
        datalabels: {
          display: function(context) {
             return context.dataset.data[context.dataIndex] > 0;
          },
          align: 'center',
          anchor: 'center',
          color: isDark ? '#fff' : '#fff',
          font: { size: 9 },
          formatter: function(value) {
            return setfFmtJutaan(value);
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.dataset.label + " (" + context.dataset.stack + "): " + setfFmtJutaan(context.raw);
            }
          }
        }
      },
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
          ticks: { color: textColor, padding: 18 } // Pushed down to make space for Budget/Realisasi labels
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
}"""

    match = old_func_pattern.search(content)
    if match:
        content = content.replace(match.group(0), new_func)
        with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched sahabat_etf.js")
    else:
        print("Could not find function to patch")

if __name__ == '__main__':
    patch_js()
