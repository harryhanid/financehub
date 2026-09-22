import os

js_path = 'app/static/js/sahabat_etf.js'
# Restore to pristine state first!
os.system(f"git checkout HEAD {js_path}")

with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# 1. Add let setfFamilyData = null; at the top
if "let setfFamilyData = null;" not in js_content:
    js_content = js_content.replace('let setfYearlyData = null;', 'let setfYearlyData = null;\nlet setfFamilyData = null;')

# 2. Update fetch logic
old_fetch = """  fetch("/beasiswa/sahabat/api/family_summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderStackedBarChart("chart-keluarga", data.families);
      setfRenderFamilyTable(data.families);
    })"""
new_fetch = """  fetch("/beasiswa/sahabat/api/family_summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfFamilyData = data;
      try { setfRenderKeluargaChart(); } catch(e) { alert("Err Keluarga Chart: " + e.message); }
      try { setfRenderFamilyTable(data.families); } catch(e) { alert("Err Keluarga Table: " + e.message); }
    })"""
js_content = js_content.replace(old_fetch, new_fetch)

# 3. Carefully replace ONLY setfRenderStackedBarChart
start_idx = js_content.find("function setfRenderStackedBarChart")
end_idx = js_content.find("\n\nfunction setfShadeColor", start_idx)

new_functions = """
function setfRenderKeluargaChart() {
  const modeEl = document.querySelector('input[name="setf-keluarga-mode"]:checked');
  const mode = modeEl ? modeEl.value : "all";
  setfRenderCustomSahabatStackedChart("chart-keluarga", "kategori_series", "name", mode);
}

function setfRenderCustomSahabatStackedChart(canvasId, dataKey, nameKey, mode) {
  const data = setfFamilyData;
  if (!data || !data.families || !data.families.length) {
    if (setfCharts[canvasId]) { setfCharts[canvasId].destroy(); delete setfCharts[canvasId]; }
    return;
  }
  
  const labels = data.families.map(f => f.label).concat(["TOTAL"]);
  const datasets = [];
  
  if (!data[dataKey]) return;
  
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
      id: 'keluargaTotalBox',
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
          ticks: { 
            color: setfThemeColor("--text-primary", "#1e293b"), 
            padding: 20, 
            font: { weight: "600" },
            callback: function(value, index, values) {
              const lbl = labels[index];
              if (lbl === "TOTAL") return lbl;
              const parts = lbl.split(" ");
              if (parts.length > 2 && parts[0] === "Sahabat") {
                  return [parts[0] + " " + parts[1], parts.slice(2).join(" ")];
              }
              return lbl;
            }
          },
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
          title: { display: true, text: "Skala Total (Juta Rp)", color: setfThemeColor("--text-secondary", "#64748b"), font: { size: 10 } }
        }
      }
    }
  });
}"""

js_content = js_content[:start_idx] + new_functions + js_content[end_idx:]

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Safely patched JS!")
