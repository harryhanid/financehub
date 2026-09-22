import os

js_path = 'app/static/js/sahabat_etf.js'
with open(js_path, 'r', encoding='utf-8') as f:
    content = f.read()

custom_yearly_chart = """
function setfRenderCustomYearlyStackedChart(canvasId, dataKey, nameKey, mode) {
  const data = setfYearlyData;
  if (!data || !data.years || !data.years.length) {
    if (setfCharts[canvasId]) { setfCharts[canvasId].destroy(); delete setfCharts[canvasId]; }
    return;
  }
  
  const labels = data.years.map(y => String(y)).concat(["TOTAL"]);
  const datasets = [];
  
  data[dataKey].forEach(function(k, idx) {
    const color = SETF_PALETTE[idx % SETF_PALETTE.length];
    
    const budgetLeft = k.budget.concat([null]);
    const actualLeft = k.realisasi.concat([null]);
    
    const totalBudget = k.budget.reduce((a,b)=>a+b, 0);
    const totalActual = k.realisasi.reduce((a,b)=>a+b, 0);
    
    const budgetRight = k.budget.map(()=>null).concat([totalBudget]);
    const actualRight = k.realisasi.map(()=>null).concat([totalActual]);
    
    if (mode === "all" || mode === "budget") {
      datasets.push({ 
        label: k[nameKey], data: budgetLeft, backgroundColor: color, stack: "Bgt", yAxisID: "y", 
        categoryPercentage: 0.8, barPercentage: 0.9, hiddenLegend: false 
      });
      datasets.push({ 
        label: k[nameKey] + " (BgtTot)", data: budgetRight, backgroundColor: color, stack: "Bgt", yAxisID: "y2", 
        categoryPercentage: 0.8, barPercentage: 0.9, hiddenLegend: true 
      });
    }
    
    if (mode === "all" || mode === "realisasi") {
      datasets.push({ 
        label: k[nameKey] + (mode === "all" ? " (Act)" : ""), data: actualLeft, backgroundColor: color, stack: "Act", yAxisID: "y", 
        categoryPercentage: 0.8, barPercentage: 0.9, hiddenLegend: (mode === "all") 
      });
      datasets.push({ 
        label: k[nameKey] + " (ActTot)", data: actualRight, backgroundColor: color, stack: "Act", yAxisID: "y2", 
        categoryPercentage: 0.8, barPercentage: 0.9, hiddenLegend: true 
      });
    }
  });

  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  
  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    plugins: [ChartDataLabels, {
      id: 'yearlyTotalBox',
      beforeDatasetsDraw: (chart) => {
        const ctx = chart.ctx;
        if (!labels || labels.length === 0) return;
        
        const tickWidth = (chart.chartArea.right - chart.chartArea.left) / labels.length;
        const leftX = chart.chartArea.right - tickWidth;
        const rightX = chart.chartArea.right;
        
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = setfThemeColor("--border-color", "#94a3b8");
        ctx.lineWidth = 1;
        ctx.rect(leftX, chart.chartArea.top, rightX - leftX, chart.chartArea.bottom - chart.chartArea.top);
        ctx.stroke();
        
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

        const bgtIndex = chart.data.datasets.findIndex(d => d.stack === "Bgt");
        const actIndex = chart.data.datasets.findIndex(d => d.stack === "Act");
        
        const metaBgt = bgtIndex >= 0 ? chart.getDatasetMeta(bgtIndex) : null;
        const metaAct = actIndex >= 0 ? chart.getDatasetMeta(actIndex) : null;
        
        for (let i = 0; i < labels.length; i++) {
           const yPos = xAxis.top + 4;
           if (metaBgt && metaBgt.data[i]) ctx.fillText('Bgt', metaBgt.data[i].x, yPos);
           if (metaAct && metaAct.data[i]) ctx.fillText('Act', metaAct.data[i].x, yPos);
        }
        ctx.restore();
      }
    }],
    options: {
      responsive: true, maintainAspectRatio: false,
      layout: { padding: { top: 20 } },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'top', align: 'end',
          labels: { 
            usePointStyle: true, boxWidth: 8,
            color: setfThemeColor("--text-primary", "#1e293b"),
            filter: function(item, data) {
               const ds = data.datasets[item.datasetIndex];
               return !ds.hiddenLegend;
            }
          }
        },
        datalabels: {
          anchor: "end", align: "top",
          color: setfThemeColor("--text-primary", "#1e293b"),
          font: { size: 9, weight: "bold" },
          formatter: function(value, context) {
            if (!value) return "";
            const dsIndex = context.datasetIndex;
            const idx = context.dataIndex;
            const stackId = context.chart.data.datasets[dsIndex].stack;
            
            let lastDsIndex = -1;
            let sum = 0;
            for (let i = 0; i < context.chart.data.datasets.length; i++) {
               const iterDs = context.chart.data.datasets[i];
               if (iterDs.stack === stackId) {
                  const val = iterDs.data[idx];
                  if (val) {
                     sum += val;
                     lastDsIndex = i;
                  }
               }
            }
            if (dsIndex === lastDsIndex) {
               return (sum / 1000000).toFixed(1);
            }
            return ""; 
          }
        }
      },
      scales: {
        x: {
          stacked: true,
          ticks: { color: setfThemeColor("--text-primary", "#1e293b"), padding: 20, font: { weight: "600" } },
          grid: { display: false }
        },
        y: {
          stacked: true, position: 'left',
          ticks: { color: setfThemeColor("--text-secondary", "#64748b"), callback: function(value) { return (value / 1000000).toFixed(1); } },
          grid: { color: "rgba(148,163,184,0.1)" },
          title: { display: false }
        },
        y2: {
          stacked: true, position: 'right',
          ticks: { color: setfThemeColor("--text-secondary", "#64748b"), callback: function(value) { return (value / 1000000).toFixed(1); } },
          grid: { display: false },
          title: { display: true, text: 'Skala Total (Juta Rp)', color: setfThemeColor("--text-secondary", "#64748b"), font: { size: 10 } }
        }
      }
    }
  });
}
"""

def safe_replace(content, func_name, element_id, data_key, name_key):
    # Find the start of the chart logic block inside the function
    start_str = "  const labels = data.years.map(y => String(y));"
    
    # We find the function definition first
    func_start = content.find(f"function {func_name}()")
    if func_start == -1: return content, False
    
    # Within this function, find where the chart logic begins
    logic_start = content.find(start_str, func_start)
    if logic_start == -1: return content, False
    
    # Find the end of the chart instantiation block `if(ctx) { ... }`
    chart_init_start = content.find(f'setfCharts["{element_id}"] = new Chart(', logic_start)
    if chart_init_start == -1: return content, False
    
    # Find the closing brace of `if(ctx) {`
    # We can just search for the end of the new Chart statement which ends with `});\n  }`
    end_str = "    });\n  }"
    logic_end = content.find(end_str, chart_init_start)
    if logic_end == -1: return content, False
    
    logic_end += len(end_str)
    
    new_logic = f'  setfRenderCustomYearlyStackedChart("{element_id}", "{data_key}", "{name_key}", mode);\n'
    
    new_content = content[:logic_start] + new_logic + content[logic_end:]
    return new_content, True

content, ok_kat = safe_replace(content, "setfRenderTahunanKategori", "chart-tahunan-kategori", "kategori", "name")
print("Kategori replaced:", ok_kat)

content, ok_pil = safe_replace(content, "setfRenderTahunanPillar", "chart-tahunan-pillar", "pillar", "name")
print("Pillar replaced:", ok_pil)

content = custom_yearly_chart + "\n" + content

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done restoring and patching.")
