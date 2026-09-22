import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

custom_chart_func = """
function setfRenderKategoriChartCustom(canvasId, kategoriRows) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();

  // Sort or just use as-is
  const labels = kategoriRows.map(k => k.cat1).concat(["TOTAL"]);
  
  // Left Axis Data
  const budgetLeft = kategoriRows.map(k => k.budget).concat([null]);
  const actualLeft = kategoriRows.map(k => k.realisasi).concat([null]);
  
  // Right Axis Data
  const totalBudget = kategoriRows.reduce((sum, k) => sum + k.budget, 0);
  const totalActual = kategoriRows.reduce((sum, k) => sum + k.realisasi, 0);
  
  const budgetRight = kategoriRows.map(k => null).concat([totalBudget]);
  const actualRight = kategoriRows.map(k => null).concat([totalActual]);

  const colorBudget = "#cbd5e1"; // light grey-blue
  const colorActual = "#3b82f6"; // bright blue

  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        { label: "Budget", data: budgetLeft, backgroundColor: colorBudget, yAxisID: "y", categoryPercentage: 0.8, barPercentage: 0.9 },
        { label: "Actual", data: actualLeft, backgroundColor: colorActual, yAxisID: "y", categoryPercentage: 0.8, barPercentage: 0.9 },
        { label: "Budget (Total)", data: budgetRight, backgroundColor: colorBudget, yAxisID: "y2", categoryPercentage: 0.8, barPercentage: 0.9 },
        { label: "Actual (Total)", data: actualRight, backgroundColor: colorActual, yAxisID: "y2", categoryPercentage: 0.8, barPercentage: 0.9 }
      ]
    },
    plugins: [ChartDataLabels, {
      id: 'customTotalBox',
      beforeDraw: (chart) => {
        const ctx = chart.ctx;
        const xAxis = chart.scales.x;
        const yAxis = chart.scales.y;
        if (!xAxis || !yAxis) return;
        
        const lastIndex = labels.length - 1;
        // get bounding box for the TOTAL category
        const tickWidth = xAxis.getPixelForTick(1) - xAxis.getPixelForTick(0);
        const center = xAxis.getPixelForTick(lastIndex);
        const leftX = center - tickWidth/2;
        const rightX = center + tickWidth/2;
        
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = setfThemeColor("--border-color", "#cbd5e1");
        ctx.lineWidth = 1;
        ctx.rect(leftX, chart.chartArea.top, rightX - leftX, chart.chartArea.bottom - chart.chartArea.top);
        ctx.stroke();
        
        // draw slightly gray background for total box
        ctx.fillStyle = "rgba(241, 245, 249, 0.3)";
        ctx.fill();
        ctx.restore();
      },
      afterDraw: (chart) => {
        const ctx = chart.ctx;
        const xAxis = chart.scales.x;
        
        ctx.save();
        ctx.font = '10px Arial';
        ctx.fillStyle = setfThemeColor("--text-muted", "#94a3b8");
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        const metaBgt = chart.getDatasetMeta(0);
        const metaAct = chart.getDatasetMeta(1);
        const metaBgtTotal = chart.getDatasetMeta(2);
        const metaActTotal = chart.getDatasetMeta(3);
        
        for (let i = 0; i < labels.length; i++) {
           const yPos = xAxis.top + 4;
           if (i === labels.length - 1) {
             if(metaBgtTotal.data[i] && metaActTotal.data[i]) {
                ctx.fillText('Bgt', metaBgtTotal.data[i].x, yPos);
                ctx.fillText('Act', metaActTotal.data[i].x, yPos);
             }
           } else {
             if(metaBgt.data[i] && metaAct.data[i]) {
                ctx.fillText('Bgt', metaBgt.data[i].x, yPos);
                ctx.fillText('Act', metaAct.data[i].x, yPos);
             }
           }
        }
        ctx.restore();
      }
    }],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: { top: 20 }
      },
      plugins: {
        legend: {
          position: 'top',
          align: 'end',
          labels: { 
            color: setfThemeColor("--text-primary", "#1e293b"),
            usePointStyle: true,
            boxWidth: 8,
            filter: function(item, chart) {
              return !item.text.includes('(Total)');
            }
          }
        },
        datalabels: {
          anchor: "end",
          align: "top",
          color: setfThemeColor("--text-primary", "#1e293b"),
          font: { size: 10, weight: "bold" },
          formatter: function(value) {
            if (value === null || value === 0) return "";
            return (value / 1000000).toFixed(1);
          }
        }
      },
      scales: {
        x: {
          ticks: { 
            color: setfThemeColor("--text-primary", "#1e293b"),
            padding: 20,
            font: { weight: "600" }
          },
          grid: { display: false }
        },
        y: {
          position: 'left',
          ticks: {
            color: setfThemeColor("--text-secondary", "#64748b"),
            callback: function(value) { return (value / 1000000).toFixed(1); }
          },
          grid: { color: "rgba(148,163,184,0.1)" },
          title: { display: false }
        },
        y2: {
          position: 'right',
          ticks: {
            color: setfThemeColor("--text-secondary", "#64748b"),
            callback: function(value) { return (value / 1000000).toFixed(1); }
          },
          grid: { display: false },
          title: { display: true, text: 'Skala Total (Juta Rp)', color: setfThemeColor("--text-secondary", "#64748b"), font: { size: 10 } }
        }
      }
    }
  });
}
"""

old_call = """      setfRenderBarChart("chart-kategori",
        data.kategori.map(function(k) { return k.cat1; }),
        [
          { label: "Budget", data: data.kategori.map(function(k) { return k.budget; }), backgroundColor: "#3b82f6" },
          { label: "Actual", data: data.kategori.map(function(k) { return k.realisasi; }), backgroundColor: "#10b981" }
        ],
        function(idx) { setfSetKategoriDrilldown(data.kategori[idx].cat1); }
      );"""

new_call = """      setfRenderKategoriChartCustom("chart-kategori", data.kategori);"""

js_content = custom_chart_func + "\n" + js_content.replace(old_call, new_call)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Kategori Chart patched")
