import sys

def patch():
    with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'r', encoding='utf-8') as f:
        content = f.read()

    old_func = """function setfRenderStackedGroupedChart(canvasId, labels, dataList) {
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
      ctx.font = "10px Inter, sans-serif";
      ctx.fillStyle = isDark ? "#94a3b8" : "#64748b";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      
      const yAxis = chart.scales.y;
      
      chart.data.labels.forEach((_, index) => {
        let metaB = chart.getDatasetMeta(0);
        let metaR = chart.getDatasetMeta(1);
        
        if (metaB && metaB.data[index]) {
           let xB = metaB.data[index].x;
           ctx.fillText("Budget", xB, yAxis.bottom + 6);
        }
        if (metaR && metaR.data[index]) {
           let xR = metaR.data[index].x;
           ctx.fillText("Realisasi", xR, yAxis.bottom + 6);
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
               // Only show one item per category by filtering even index
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
          color: '#fff',
          font: { size: 9, weight: 'bold' },
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
          ticks: { color: textColor, padding: 20 }
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

    if old_func in content:
        content = content.replace(old_func, new_func)
        with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched sahabat_etf.js")
    else:
        print("Could not find old func")

if __name__ == '__main__':
    patch()
