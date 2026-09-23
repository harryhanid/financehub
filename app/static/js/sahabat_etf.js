
document.addEventListener("DOMContentLoaded", function() {
    let checkExist = setInterval(function() {
        let chartDiv = document.getElementById("tree-chart");
        if (chartDiv) {
            clearInterval(checkExist);
            chartDiv.addEventListener("wheel", function(e) {
                e.stopPropagation();
            }, { capture: true });
        }
    }, 100);
});


window.treeSpacingMultiplier = 1.0;



  let uidCounter = 0;
  function assignUID(node) {
      if (!node) return;
      node._uid = ++uidCounter;
      if (node.children) node.children.forEach(assignUID);
  }

  function applyInitialDepth(node, currentDepth, maxDepth) {
      if (!node) return;
      if (currentDepth >= maxDepth && node.children && node.children.length > 0) {
          node.collapsed = true;
      } else {
          node.collapsed = false;
      }
      if (node.children) {
          node.children.forEach(c => applyInitialDepth(c, currentDepth + 1, maxDepth));
      }
  }

  
  function getVisibleDepth(node, currentDepth) {
      if (!node) return currentDepth;
      if (node.collapsed || !node.children || node.children.length === 0) {
          return currentDepth;
      }
      let maxD = currentDepth;
      node.children.forEach(c => {
          let d = getVisibleDepth(c, currentDepth + 1);
          if (d > maxD) maxD = d;
      });
      return maxD;
  }

  function countVisibleLeaves(node) {
      if (!node) return 1;
      if (node.collapsed || !node.children || node.children.length === 0) {
          return 1;
      }
      let sum = 0;
      node.children.forEach(c => sum += countVisibleLeaves(c));
      return sum;
  }


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
        ctx.strokeStyle = "rgba(255, 205, 86, 1)";
        ctx.lineWidth = 1;
        ctx.rect(leftX, chart.chartArea.top, rightX - leftX, chart.chartArea.bottom - chart.chartArea.top);
        ctx.stroke();
        
        // draw slightly gray background for total box
        ctx.fillStyle = "rgba(255, 205, 86, 0.2)";
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
            },
            onClick: function(e, legendItem, legend) {
              const index = legendItem.datasetIndex;
              const ci = legend.chart;
              const isVisible = ci.isDatasetVisible(index);
              ci.setDatasetVisibility(index, !isVisible);
              
              const baseLabel = ci.data.datasets[index].label;
              let targetLabel = "";
              if (baseLabel === "Budget") targetLabel = "Budget (Total)";
              else if (baseLabel === "Actual") targetLabel = "Actual (Total)";
              else if (baseLabel.endsWith(" (Act)")) targetLabel = baseLabel.replace(" (Act)", " (ActTot)");
              else targetLabel = baseLabel + " (BgtTot)";

              ci.data.datasets.forEach((ds, i) => {
                if (ds.label === targetLabel) {
                  ci.setDatasetVisibility(i, !isVisible);
                }
              });
              ci.update();
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
        ctx.strokeStyle = "rgba(255, 205, 86, 1)";
        ctx.lineWidth = 1;
        ctx.rect(leftX, chart.chartArea.top, rightX - leftX, chart.chartArea.bottom - chart.chartArea.top);
        ctx.stroke();
        
        ctx.fillStyle = "rgba(255, 205, 86, 0.2)";
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
            },
            onClick: function(e, legendItem, legend) {
              const index = legendItem.datasetIndex;
              const ci = legend.chart;
              const isVisible = ci.isDatasetVisible(index);
              ci.setDatasetVisibility(index, !isVisible);
              
              const baseLabel = ci.data.datasets[index].label;
              let targetLabel = "";
              if (baseLabel === "Budget") targetLabel = "Budget (Total)";
              else if (baseLabel === "Actual") targetLabel = "Actual (Total)";
              else if (baseLabel.endsWith(" (Act)")) targetLabel = baseLabel.replace(" (Act)", " (ActTot)");
              else targetLabel = baseLabel + " (BgtTot)";

              ci.data.datasets.forEach((ds, i) => {
                if (ds.label === targetLabel) {
                  ci.setDatasetVisibility(i, !isVisible);
                }
              });
              ci.update();
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


function setfRenderCustomBudgetChart(canvasId, dataRows, labelKey) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();

  // Sort or just use as-is
  const labels = dataRows.map(k => k[labelKey]).concat(["TOTAL"]);
  
  // Left Axis Data
  const budgetLeft = dataRows.map(k => k.budget).concat([null]);
  const actualLeft = dataRows.map(k => k.realisasi).concat([null]);
  
  // Right Axis Data
  const totalBudget = dataRows.reduce((sum, k) => sum + k.budget, 0);
  const totalActual = dataRows.reduce((sum, k) => sum + k.realisasi, 0);
  
  const budgetRight = dataRows.map(k => null).concat([totalBudget]);
  const actualRight = dataRows.map(k => null).concat([totalActual]);

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
      beforeDatasetsDraw: (chart) => {
        const ctx = chart.ctx;
        const xAxis = chart.scales.x;
        const yAxis = chart.scales.y;
        if (!xAxis || !yAxis) return;
        
        if (!labels || labels.length === 0) return;
        
        // Mathematical absolute calculation for the last column (TOTAL)
        const tickWidth = (chart.chartArea.right - chart.chartArea.left) / labels.length;
        const leftX = chart.chartArea.right - tickWidth;
        const rightX = chart.chartArea.right;
        
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = "rgba(255, 205, 86, 1)";
        ctx.lineWidth = 1;
        ctx.rect(leftX, chart.chartArea.top, rightX - leftX, chart.chartArea.bottom - chart.chartArea.top);
        ctx.stroke();
        
        ctx.fillStyle = "rgba(255, 205, 86, 0.2)";
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
            },
            onClick: function(e, legendItem, legend) {
              const index = legendItem.datasetIndex;
              const ci = legend.chart;
              const isVisible = ci.isDatasetVisible(index);
              ci.setDatasetVisibility(index, !isVisible);
              
              const baseLabel = ci.data.datasets[index].label;
              let targetLabel = "";
              if (baseLabel === "Budget") targetLabel = "Budget (Total)";
              else if (baseLabel === "Actual") targetLabel = "Actual (Total)";
              else if (baseLabel.endsWith(" (Act)")) targetLabel = baseLabel.replace(" (Act)", " (ActTot)");
              else targetLabel = baseLabel + " (BgtTot)";

              ci.data.datasets.forEach((ds, i) => {
                if (ds.label === targetLabel) {
                  ci.setDatasetVisibility(i, !isVisible);
                }
              });
              ci.update();
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


const setfStackTotalPlugin = {
  id: "setfStackTotal",
  afterDatasetsDraw: function (chart) {
    const totals = {};
    chart.data.datasets.forEach(function (ds) {
      if (!ds.hidden) {
        ds.data.forEach(function (v, i) { totals[i] = (totals[i] || 0) + (v || 0); });
      }
    });
    const meta = chart.getDatasetMeta(0);
    if (!meta || !meta.data.length) return;
    const ctx = chart.ctx;
    const yScale = chart.scales.y;
    ctx.save();
    ctx.font = "bold 10px sans-serif";
    ctx.fillStyle = setfThemeColor("--text-primary", "#e2e8f0");
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    meta.data.forEach(function (bar, i) {
      const total = totals[i] || 0;
      if (!total) return;
      ctx.fillText(setfFmtJutaan(total), bar.x, yScale.getPixelForValue(total) - 4);
    });
    ctx.restore();
  }
};

const setfTotalZonePlugin = {
  id: 'totalZone',
  beforeDraw: function(chart) {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const ctx = chart.ctx;
    const xAxis = chart.scales.x;
    const yAxisRight = chart.scales['y-right'];
    if (!xAxis || !yAxisRight) return;
    
    let totalIndex = -1;
    xAxis.getTicks().forEach((tick, i) => {
       if (tick.label === "TOTAL") totalIndex = i;
    });
    if (totalIndex === -1) return;
    
    const leftX = totalIndex === 0 ? xAxis.left : (xAxis.getPixelForTick(totalIndex - 1) + xAxis.getPixelForTick(totalIndex)) / 2;
    const rightX = xAxis.right;
    
    const topY = chart.chartArea.top;
    const bottomY = chart.chartArea.bottom;
    
    ctx.save();
    ctx.beginPath();
    ctx.setLineDash([5, 5]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(255, 205, 86, 1)";
    ctx.rect(leftX, topY, rightX - leftX, bottomY - topY);
    ctx.stroke();
    
    ctx.fillStyle = "rgba(255, 205, 86, 0.2)";
    ctx.fill();
    ctx.restore();
  }
};



const SETF_CAT_BADGE_CLASS = {
  "By Pendidikan": "badge-cat-by-pendidikan",
  "By Tunjangan": "badge-cat-by-tunjangan",
  "By Penelitian": "badge-cat-by-penelitian",
  "By Medical": "badge-cat-by-medical",
};

const SETF_STATUS_BADGE_CLASS = {
  "Aktif": "badge-status-active",
  "lulus": "badge-status-completed",
  "gugur": "badge-status-expired",
  "undur diri": "badge-status-near-limit",
};

const SETF_JENJANG_BADGE_CLASS = {
  "SD": "setf-badge-jenjang-sd",
  "SMP": "setf-badge-jenjang-smp",
  "SMA": "setf-badge-jenjang-sma",
  "SMK": "setf-badge-jenjang-smk",
  "S1": "setf-badge-jenjang-s1",
  "S2": "setf-badge-jenjang-s2",
  "S3": "setf-badge-jenjang-s3",
  "SETF": "setf-badge-jenjang-setf",
};

function setfHexToRgba(hex, alpha) {
    let r = parseInt(hex.slice(1, 3), 16),
        g = parseInt(hex.slice(3, 5), 16),
        b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// static/js/sahabat_etf.js
let setfCharts = {};


const SETF_BULAN_LABEL = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const SETF_PALETTE = ["#6366f1", "#818cf8", "#f97316", "#06b6d4", "#10b981", "#f59e0b", "#a855f7", "#ec4899", "#ef4444", "#8b5cf6"];
const setfCategoryColorMap = {};

function setfRenderAlert(overBudget) {
  const card = document.getElementById("setf-alert-card");
  const list = document.getElementById("setf-alert-list");
  if (!card || !list) return;
  if (!overBudget || !overBudget.length) {
    card.style.display = "none";
    return;
  }
  card.style.display = "block";
  list.innerHTML = overBudget.map(function (o) {
    return "<li>" + o.nama + " — realisasi melebihi budget sebesar " + setfFmtJutaan(o.selisih) + "</li>";
  }).join("");
}

function setfSisaCell(amount) {
  const cls = (amount || 0) < 0 ? ' class="setf-sisa-negative"' : "";
  return "<td" + cls + ">" + setfFmtJutaan(amount) + "</td>";
}

function setfThemeColor(varName, fallback) {
  const page = document.querySelector(".budget-page");
  const val = page ? getComputedStyle(page).getPropertyValue(varName).trim() : "";
  return val || fallback;
}

function setfJenjangBadge(jenjang) {
  if (!jenjang) return "";
  const cls = SETF_JENJANG_BADGE_CLASS[jenjang] || "setf-badge-jenjang-lainnya";
  return '<span class="setf-badge-jenjang ' + cls + '">' + jenjang + "</span>";
}

function setfFirstName(fullName) {
  return (fullName || "").trim().split(/\s+/)[0] || "";
}

function setfRenderSummaryCards(rows) {
  const totalSiswa = rows.filter(function (r) { return r.status === "Aktif"; }).length;
  const totalBudget = rows.reduce(function (s, r) { return s + r.budget_total; }, 0);
  const totalPayment = rows.reduce(function (s, r) { return s + r.payment_total; }, 0);
  const totalRealisasi = rows.reduce(function (s, r) { return s + r.realisasi_total; }, 0);
  const totalSisa = rows.reduce(function (s, r) { return s + r.sisa_budget; }, 0);
  const cards = [
    ["Total Anggota Aktif", totalSiswa, ""],
    ["Total Budget", setfFmtJutaan(totalBudget), ""],
    ["Total Klaim", setfFmtJutaan(totalPayment), ""],
    ["Total Realisasi", setfFmtJutaan(totalRealisasi), " setf-stat-realisasi"],
    ["Sisa Budget", setfFmtJutaan(totalSisa), totalSisa < 0 ? " setf-sisa-negative" : ""],
  ];
  document.getElementById("setf-summary").innerHTML = cards.map(function (c) {
    return '<div class="budget-stat-card' + c[2] + '"><div class="label">' + c[0] +
      '</div><div class="value">' + c[1] + "</div></div>";
  }).join("");
}

function setfBuildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.years.length) params.set("years", filters.years.join(","));
  if (filters.pillars.length) params.set("pillars", filters.pillars.join(","));
  return params.toString();
}

function setfMismatchCell(amount, mismatch) {
  const cls = mismatch ? ' class="setf-payment-mismatch"' : "";
  return "<td" + cls + ">" + setfFmtJutaan(amount) + "</td>";
}

function setfFmtJutaan(amount) {
  return fmtJutaan(amount);
}

function setfGetSelectedFilters() {
  const years = Array.from(document.querySelectorAll(".setf-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".setf-pillar-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars };
}

function setfRenderMonthlyTable(comparison, years) {
  const theadRow = document.getElementById("setf-monthly-thead-row");
  theadRow.innerHTML = "<th>Bulan</th>" + years.map(function (y) { return "<th>" + y + "</th>"; }).join("");

  const tbody = document.querySelector("#setf-monthly-table tbody");
  if (!comparison.length) {
    tbody.innerHTML = '<tr><td colspan="' + (years.length + 1) + '" style="text-align:center;color:var(--text-muted)">Pilih minimal 1 tahun.</td></tr>';
    return;
  }
  const allValues = [];
  comparison.forEach(function (row) {
    years.forEach(function (y) {
      const v = row.per_tahun[y] || 0;
      if (v > 0) allValues.push(v);
    });
  });
  const minVal = allValues.length ? Math.min.apply(null, allValues) : 0;
  const maxVal = allValues.length ? Math.max.apply(null, allValues) : 0;

  const rows = comparison.map(function (row) {
    const cells = years.map(function (y) {
      const v = row.per_tahun[y] || 0;
      return "<td" + setfColorScaleAttr(v, minVal, maxVal) + ">" + setfFmtJutaan(v) + "</td>";
    }).join("");
    return "<tr><td>" + SETF_BULAN_LABEL[row.bulan - 1] + "</td>" + cells + "</tr>";
  }).join("");
  const totalCells = years.map(function (y) {
    const total = comparison.reduce(function (s, row) { return s + (row.per_tahun[y] || 0); }, 0);
    return "<td>" + setfFmtJutaan(total) + "</td>";
  }).join("");
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td>" + totalCells + "</tr>";
  tbody.innerHTML = rows + totalRow;
}

function setfRenderPillarTable(pillarRows) {
  const tbody = document.querySelector("#setf-pillar-table tbody");
  if (!pillarRows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data pillar.</td></tr>';
    return;
  }
  const rows = pillarRows.map(function (p) {
    return "<tr>" +
      "<td>" + p.pillar + "</td>" +
      "<td>" + setfFmtJutaan(p.budget) + "</td>" +
      "<td>" + setfFmtJutaan(p.realisasi) + "</td>" +
      setfSisaCell(p.sisa) +
      "</tr>";
  }).join("");
  const totalBudget = pillarRows.reduce(function (s, p) { return s + p.budget; }, 0);
  const totalRealisasi = pillarRows.reduce(function (s, p) { return s + p.realisasi; }, 0);
  const totalSisa = pillarRows.reduce(function (s, p) { return s + p.sisa; }, 0);
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td>" +
    "<td>" + setfFmtJutaan(totalBudget) + "</td>" +
    "<td>" + setfFmtJutaan(totalRealisasi) + "</td>" +
    setfSisaCell(totalSisa) + "</tr>";
  tbody.innerHTML = rows + totalRow;
}

function setfRenderMonthlyChart(months) {
  setfRenderBarChart("chart-bulanan", months.map(function (m) { return SETF_BULAN_LABEL[m.bulan - 1]; }), [
    { label: "Realisasi", data: months.map(function (m) { return m.realisasi; }), backgroundColor: "#818cf8" },
  ], setfHighlightMonthlyRow);
}

function setfUpdateReportExportLink() {
  const sel = document.getElementById("setf-report-year");
  if (!sel) return;
  
  let qs = "year=" + encodeURIComponent(sel.value);
  const monthSel = document.getElementById("setf-report-month");
  if (monthSel) qs += "&month=" + encodeURIComponent(monthSel.value);
  
  const pillars = Array.from(document.querySelectorAll(".setf-laporan-pillar-cb:checked")).map(function (cb) { return cb.value; });
  pillars.forEach(function (p) { qs += "&pillars[]=" + encodeURIComponent(p); });
  
  const linkReport = document.getElementById("setf-export-report");
  if (linkReport) linkReport.href = "/beasiswa/sahabat/export/report?" + qs;

  const linkDetail = document.getElementById("setf-export-report-detail");
  if (linkDetail) linkDetail.href = "/beasiswa/sahabat/export/report/detail?" + qs;

  const linkPptFy = document.getElementById("setf-export-ppt-fy");
  if (linkPptFy) linkPptFy.href = "/beasiswa/sahabat/api/report/export_ppt?mode=fy&" + qs;

  const linkPptYtd = document.getElementById("setf-export-ppt-ytd");
  if (linkPptYtd) linkPptYtd.href = "/beasiswa/sahabat/api/report/export_ppt?mode=ytd&" + qs;
}

function onBeforePrint() { resizeCharts(); }

function setfRenderLatestPaymentsTable(rows) {
  const tbody = document.querySelector("#setf-latest-payments-table tbody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Belum ada transaksi.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.tanggal + "</td>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + setfCatBadge(r.cat1) + "</td>" +
      "<td>" + (r.cat2 || "") + "</td>" +
      '<td class="num-right">' + setfFmtJutaan(r.amount) + "</td>" +
      "</tr>";
  }).join("");
}

function setfCatBadge(cat1) {
  if (!cat1) return "";
  const cls = SETF_CAT_BADGE_CLASS[cat1] || "badge-cat-lainnya";
  return '<span class="budget-badge ' + cls + '">' + cat1 + "</span>";
}

function setfDatalabelFormatter(value) {
  return value ? setfFmtJutaan(value) : null;
}

function resizeCharts() {
    Object.keys(setfCharts).forEach(function (key) {
      if (setfCharts[key]) setfCharts[key].resize();
    });
  }

function setfCatBadgeList(kategoriCsv) {
  if (!kategoriCsv) return "";
  return kategoriCsv.split(",").map(function (c) { return setfCatBadge(c.trim()); }).join(" ");
}

function setfRenderKategoriTable(kategoriRows) {
  const tbody = document.querySelector("#setf-kategori-table tbody");
  if (!kategoriRows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data kategori.</td></tr>';
    return;
  }
  
  const pddRows = kategoriRows.filter(k => k.cat1 !== "By Medical");
  const kesRows = kategoriRows.filter(k => k.cat1 === "By Medical");
  
  let html = "";
  
  if (pddRows.length > 0) {
      html += '<tr><td colspan="4" style="font-weight:bold; font-size:1.1em; padding-top:1rem; padding-bottom:0.5rem; color:var(--text-primary)">Pendidikan</td></tr>';
      html += pddRows.map(function (k) {
        const sisa = k.budget - k.realisasi;
        return "<tr>" +
          "<td>" + setfCatBadge(k.cat1) + "</td>" +
          "<td>" + setfFmtJutaan(k.budget) + "</td>" +
          "<td>" + setfFmtJutaan(k.realisasi) + "</td>" +
          setfSisaCell(sisa) +
          "</tr>";
      }).join("");
      
      const subBgt = pddRows.reduce((s, k) => s + k.budget, 0);
      const subAct = pddRows.reduce((s, k) => s + k.realisasi, 0);
      const subSisa = subBgt - subAct;
      html += '<tr style="font-weight:bold; background:rgba(241, 245, 249, 0.5)">' +
        '<td style="color:var(--text-primary)">Sub Total Pendidikan</td>' +
        '<td style="color:var(--text-primary)">' + setfFmtJutaan(subBgt) + '</td>' +
        '<td style="color:var(--text-primary)">' + setfFmtJutaan(subAct) + '</td>' +
        '<td ' + (subSisa < 0 ? 'class="setf-sisa-negative"' : '') + '>' + setfFmtJutaan(subSisa) + '</td></tr>';
  }
  
  if (kesRows.length > 0) {
      html += '<tr><td colspan="4" style="font-weight:bold; font-size:1.1em; padding-top:1rem; padding-bottom:0.5rem; color:var(--text-primary)">Kesehatan</td></tr>';
      html += kesRows.map(function (k) {
        const sisa = k.budget - k.realisasi;
        return "<tr>" +
          "<td>" + setfCatBadge(k.cat1) + "</td>" +
          "<td>" + setfFmtJutaan(k.budget) + "</td>" +
          "<td>" + setfFmtJutaan(k.realisasi) + "</td>" +
          setfSisaCell(sisa) +
          "</tr>";
      }).join("");
      
      const subBgt = kesRows.reduce((s, k) => s + k.budget, 0);
      const subAct = kesRows.reduce((s, k) => s + k.realisasi, 0);
      const subSisa = subBgt - subAct;
      html += '<tr style="font-weight:bold; background:rgba(241, 245, 249, 0.5)">' +
        '<td style="color:var(--text-primary)">Sub Total Kesehatan</td>' +
        '<td style="color:var(--text-primary)">' + setfFmtJutaan(subBgt) + '</td>' +
        '<td style="color:var(--text-primary)">' + setfFmtJutaan(subAct) + '</td>' +
        '<td ' + (subSisa < 0 ? 'class="setf-sisa-negative"' : '') + '>' + setfFmtJutaan(subSisa) + '</td></tr>';
  }
  
  const totalBgt = kategoriRows.reduce((s, k) => s + k.budget, 0);
  const totalAct = kategoriRows.reduce((s, k) => s + k.realisasi, 0);
  const totalSisa = totalBgt - totalAct;
  html += '<tr style="font-weight:bold;">' +
    '<td style="color:var(--text-primary); font-size: 1.05em; padding-top:1rem;">Total Pendidikan dan Kesehatan</td>' +
    '<td style="color:var(--text-primary); font-size: 1.05em; padding-top:1rem;">' + setfFmtJutaan(totalBgt) + '</td>' +
    '<td style="color:var(--text-primary); font-size: 1.05em; padding-top:1rem;">' + setfFmtJutaan(totalAct) + '</td>' +
    '<td style="font-size: 1.05em; padding-top:1rem;" ' + (totalSisa < 0 ? 'class="setf-sisa-negative"' : '') + '>' + setfFmtJutaan(totalSisa) + '</td></tr>';
    
  tbody.innerHTML = html;
}

let setfYearlyData = null;
let setfFamilyData = null;

function setfRenderTahunanData(yearly) {
  setfYearlyData = yearly;
  setfRenderTahunanKategori();
  setfRenderTahunanPillar();
}

function setfRenderTahunanKategori() {
  try {
  const modeEl = document.querySelector('input[name="setf-tahunan-kat-mode"]:checked');
  const mode = modeEl ? modeEl.value : "all";
  const data = setfYearlyData;
  if (!data || !data.years || !data.years.length) {
    if (setfCharts["chart-tahunan-kategori"]) { setfCharts["chart-tahunan-kategori"].destroy(); delete setfCharts["chart-tahunan-kategori"]; }
    const tb = document.querySelector("#setf-tahunan-kategori-table tbody");


    if(tb) tb.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data.</td></tr>';
    return;
  }
  
  let tbodyHtml = "";
  data.kategori.forEach(function(k) {
    const budget = k.budget.reduce((a,b)=>a+b, 0);
    const actual = k.realisasi.reduce((a,b)=>a+b, 0);
    const sisa = budget - actual;
    tbodyHtml += "<tr><td>" + k.name + '</td><td class="num-right">' + setfFmtJutaan(budget) + '</td><td class="num-right">' + setfFmtJutaan(actual) + '</td>' + setfSisaCell(sisa) + '</tr>';
  });
  const grandBudget = data.kategori.reduce((s, k) => s + k.budget.reduce((a,b)=>a+b,0), 0);
  const grandActual = data.kategori.reduce((s, k) => s + k.realisasi.reduce((a,b)=>a+b,0), 0);
  const grandSisa = grandBudget - grandActual;
  tbodyHtml += '<tr style="font-weight:bold"><td>Total</td><td class="num-right">' + setfFmtJutaan(grandBudget) + '</td><td class="num-right">' + setfFmtJutaan(grandActual) + '</td>' + setfSisaCell(grandSisa) + '</tr>';
  const tb = document.querySelector("#setf-tahunan-kategori-table tbody");


  if(tb) tb.innerHTML = tbodyHtml;

  setfRenderCustomYearlyStackedChart("chart-tahunan-kategori", "kategori", "name", mode);
  } catch(e) {
    console.error("Error in setfRenderTahunanKategori:", e);
    alert("Error in setfRenderTahunanKategori: " + e.message);
  }
}

function setfRenderTahunanPillar() {
  try {
  const modeEl = document.querySelector('input[name="setf-tahunan-pil-mode"]:checked');
  const mode = modeEl ? modeEl.value : "all";
  const data = setfYearlyData;
  if (!data || !data.years || !data.years.length) {
    if (setfCharts["chart-tahunan-pillar"]) { setfCharts["chart-tahunan-pillar"].destroy(); delete setfCharts["chart-tahunan-pillar"]; }
    const tb = document.querySelector("#setf-tahunan-pillar-table tbody");


    if(tb) tb.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">Belum ada data.</td></tr>';
    return;
  }
  
  let tbodyHtml = "";
  data.pillar.forEach(function(k) {
    const budget = k.budget.reduce((a,b)=>a+b, 0);
    const actual = k.realisasi.reduce((a,b)=>a+b, 0);
    const sisa = budget - actual;
    tbodyHtml += "<tr><td>" + k.name + '</td><td class="num-right">' + setfFmtJutaan(budget) + '</td><td class="num-right">' + setfFmtJutaan(actual) + '</td>' + setfSisaCell(sisa) + '</tr>';
  });
  const grandBudget = data.pillar.reduce((s, k) => s + k.budget.reduce((a,b)=>a+b,0), 0);
  const grandActual = data.pillar.reduce((s, k) => s + k.realisasi.reduce((a,b)=>a+b,0), 0);
  const grandSisa = grandBudget - grandActual;
  tbodyHtml += '<tr style="font-weight:bold"><td>Total</td><td class="num-right">' + setfFmtJutaan(grandBudget) + '</td><td class="num-right">' + setfFmtJutaan(grandActual) + '</td>' + setfSisaCell(grandSisa) + '</tr>';
  const tb = document.querySelector("#setf-tahunan-pillar-table tbody");


  if(tb) tb.innerHTML = tbodyHtml;

  setfRenderCustomYearlyStackedChart("chart-tahunan-pillar", "pillar", "name", mode);
  } catch(e) {
    console.error("Error in setfRenderTahunanPillar:", e);
    alert("Error in setfRenderTahunanPillar: " + e.message);
  }
}



function setfRenderDoughnutChart(canvasId, labels, values, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
    plugins: [ChartDataLabels],
    options: {
      responsive: true,
      onClick: function (evt, elements) {
        if (!elements.length) return;
        setfSetKategoriDrilldown(labels[elements[0].index]);
      },
      plugins: {
        legend: { position: "right", labels: { color: setfThemeColor("--text-primary", "#e2e8f0") } },
        datalabels: {
          anchor: "center",
          align: "center",
          color: "#fff",
          font: { size: 10, weight: "600" },
          formatter: setfDatalabelFormatter,
        },
      },
    },
  });
}

function setfStatusBadge(status) {
  if (!status) return "";
  const cls = SETF_STATUS_BADGE_CLASS[status] || "badge-status-active";
  return '<span class="budget-badge ' + cls + '">' + status + "</span>";
}

function setfRenderBarChart(canvasId, labels, datasets, onBarClick) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (setfCharts[canvasId]) setfCharts[canvasId].destroy();
  setfCharts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    plugins: [ChartDataLabels],
    options: {
      responsive: true,
      onClick: function (evt, elements) {
        if (!elements.length || !onBarClick) return;
        onBarClick(elements[0].index);
      },
      plugins: {
        legend: { labels: { color: setfThemeColor("--text-primary", "#e2e8f0") } },
        datalabels: {
          anchor: "end",
          align: "top",
          color: setfThemeColor("--text-primary", "#e2e8f0"),
          font: { size: 10, weight: "600" },
          formatter: setfDatalabelFormatter,
        },
      },
      scales: {
        x: { ticks: { color: setfThemeColor("--text-secondary", "#94a3b8") }, grid: { color: "rgba(148,163,184,0.1)" } },
        y: {
          ticks: {
            color: setfThemeColor("--text-secondary", "#94a3b8"),
            callback: function (value) { return setfFmtJutaan(value); },
          },
          grid: { color: "rgba(148,163,184,0.1)" },
        },
      },
    },
  });
}

function setfRenderTable(rows) {
  const tbody = document.querySelector("#setf-table tbody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Belum ada anggota Sahabat ETF.</td></tr>';
    return;
  }
  const rowsHtml = rows.map(function (r) {
    const mismatch = Math.round(r.payment_total) !== Math.round(r.realisasi_total);
    return "<tr>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + setfJenjangBadge(r.jenjang) + "</td>" +
      "<td>" + r.angkatan + "</td>" +
      "<td>" + setfStatusBadge(r.status) + "</td>" +
      "<td>" + setfFmtJutaan(r.budget_total) + "</td>" +
      setfMismatchCell(r.payment_total, mismatch) +
      setfMismatchCell(r.realisasi_total, mismatch) +
      setfSisaCell(r.sisa_budget) +
      "</tr>";
  }).join("");
  const totalBudget = rows.reduce(function (s, r) { return s + r.budget_total; }, 0);
  const totalPayment = rows.reduce(function (s, r) { return s + r.payment_total; }, 0);
  const totalRealisasi = rows.reduce(function (s, r) { return s + r.realisasi_total; }, 0);
  const totalSisa = rows.reduce(function (s, r) { return s + r.sisa_budget; }, 0);
  const totalMismatch = Math.round(totalPayment) !== Math.round(totalRealisasi);
  const totalRow = "<tr style=\"font-weight:bold\"><td>Total</td><td></td><td></td><td></td>" +
    "<td>" + setfFmtJutaan(totalBudget) + "</td>" +
    setfMismatchCell(totalPayment, totalMismatch) +
    setfMismatchCell(totalRealisasi, totalMismatch) +
    setfSisaCell(totalSisa) + "</tr>";
  tbody.innerHTML = rowsHtml + totalRow;
}

function setfRenderSummarySkeleton() {
  document.getElementById("setf-summary").innerHTML = Array(5).fill(0).map(function () {
    return '<div class="budget-stat-card"><div class="label">&nbsp;</div>' +
      '<div class="fh-skel" style="width:70%;height:20px;margin-top:.25rem"></div></div>';
  }).join("");
}

function setfColorForCategory(name) {
  if (!setfCategoryColorMap[name]) {
    const idx = Object.keys(setfCategoryColorMap).length % SETF_PALETTE.length;
    setfCategoryColorMap[name] = SETF_PALETTE[idx];
  }
  return setfCategoryColorMap[name];
}

function restore() {
    accordions.forEach(function (d, i) { d.open = prevState[i]; });
    window.removeEventListener("beforeprint", onBeforePrint);
    window.removeEventListener("afterprint", restore);
  }


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
        ctx.strokeStyle = "rgba(255, 205, 86, 1)";
        ctx.lineWidth = 1;
        ctx.rect(leftX, chart.chartArea.top, rightX - leftX, chart.chartArea.bottom - chart.chartArea.top);
        ctx.stroke();
        
        ctx.fillStyle = "rgba(255, 205, 86, 0.2)";
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
            },
            onClick: function(e, legendItem, legend) {
              const index = legendItem.datasetIndex;
              const ci = legend.chart;
              const isVisible = ci.isDatasetVisible(index);
              ci.setDatasetVisibility(index, !isVisible);
              
              const baseLabel = ci.data.datasets[index].label;
              let targetLabel = "";
              if (baseLabel === "Budget") targetLabel = "Budget (Total)";
              else if (baseLabel === "Actual") targetLabel = "Actual (Total)";
              else if (baseLabel.endsWith(" (Act)")) targetLabel = baseLabel.replace(" (Act)", " (ActTot)");
              else targetLabel = baseLabel + " (BgtTot)";

              ci.data.datasets.forEach((ds, i) => {
                if (ds.label === targetLabel) {
                  ci.setDatasetVisibility(i, !isVisible);
                }
              });
              ci.update();
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
}

function setfShadeColor(hex, percent) {
  const num = parseInt(hex.replace("#", ""), 16);
  const amt = Math.round(2.55 * percent);
  let r = (num >> 16) + amt;
  let g = ((num >> 8) & 0x00ff) + amt;
  let b = (num & 0x0000ff) + amt;
  r = Math.min(255, Math.max(0, r));
  g = Math.min(255, Math.max(0, g));
  b = Math.min(255, Math.max(0, b));
  return "#" + (0x1000000 + r * 0x10000 + g * 0x100 + b).toString(16).slice(1);
}

function setfUpdateExportLinks(qs) {
  const summaryLink = document.getElementById("setf-export-summary");
  const baseSummary = summaryLink.href.split("?")[0];
  summaryLink.href = qs ? baseSummary + "?" + qs : baseSummary;
}

function setfColorScaleAttr(value, min, max) {
  if (!value) return "";
  const alpha = max > min ? 0.12 + ((value - min) / (max - min)) * 0.4 : 0.35;
  return ' style="background-color:rgba(99,102,241,' + alpha.toFixed(2) + ')"';
}



let setfActiveKategoriDrilldown = null;

function setfExpandGrafik() {
  const details = document.getElementById("setf-grafik-accordion");
  if (!details) return;
  if (!details.open) details.open = true;
}

function setfHighlightMonthlyRow(bulanIndex) {
  setfExpandGrafik();
  const tbody = document.querySelector("#setf-monthly-table tbody");
  if (!tbody) return;
  const rows = tbody.querySelectorAll("tr");
  rows.forEach(function (tr) { tr.classList.remove("setf-row-highlight"); });
  const target = rows[bulanIndex];
  if (target) {
    target.classList.add("setf-row-highlight");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function setfRenderDrilldownChip() {
  const chip = document.getElementById("setf-drilldown-chip");
  if (!chip) return;
  if (!setfActiveKategoriDrilldown) {
    chip.style.display = "none";
    chip.innerHTML = "";
    return;
  }
  chip.style.display = "inline-flex";
  chip.innerHTML = "Filter aktif: Kategori = " + setfActiveKategoriDrilldown +
    ' <button type="button" class="budget-btn" style="padding:.15rem .6rem;font-size:.72rem" ' +
    'onclick="setfClearKategoriDrilldown()">Hapus filter</button>';
}

function setfRefetchLatestPayments() {
  const filters = setfGetSelectedFilters();
  const params = new URLSearchParams(setfBuildQueryString(filters));
  if (setfActiveKategoriDrilldown) params.set("kategori", setfActiveKategoriDrilldown);
  fetch("/beasiswa/sahabat/api/latest_payments?" + params.toString())
    .then(function (r) { return r.json(); })
    .then(function (data) { setfRenderLatestPaymentsTable(data.rows); })
    .catch(function () { showToast("Gagal memuat 10 transaksi terakhir.", "error"); });
}

function setfSetKategoriDrilldown(kategoriName) {
  setfActiveKategoriDrilldown = kategoriName;
  setfRenderDrilldownChip();
  setfExpandGrafik();
  setfRefetchLatestPayments();
  const table = document.getElementById("setf-latest-payments-table");
  if (table) table.scrollIntoView({ behavior: "smooth", block: "center" });
}

function setfClearKategoriDrilldown() {
  setfActiveKategoriDrilldown = null;
  setfRenderDrilldownChip();
  setfRefetchLatestPayments();
}


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

  const budgetColors = labels.map(l => l === "TOTAL" ? (isDark ? "#475569" : "#cbd5e1") : setfColorForCategory(l) + "66");
  const realisasiColors = labels.map(l => l === "TOTAL" ? (isDark ? "#3b82f6" : "#3b82f6") : setfColorForCategory(l));

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
        if (lbl !== "TOTAL" && canvasId === "chart-kategori") {
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
function setfRenderStackedGroupedChart(canvasId, years, dataList, mode) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";

    let activeItems = dataList;
    let rawDatasets = [];
    let showBudget = (mode === "all" || mode === "budget" || !mode);
    let showActual = (mode === "all" || mode === "actual" || mode === "realisasi" || !mode);

    const shapes = ['dot', 'diagonal-right-left', 'square', 'zigzag', 'triangle', 'weave', 'cross'];
    activeItems.forEach(function(item, idx) {
       let shape = shapes[idx % shapes.length];
       let color = setfColorForCategory(item.originalName || item.name);
       if (canvasId.includes("pillar")) {
           if (item.name === "AGRI") color = "#10b981";
           else if (item.name === "APP") color = "#3b82f6";
           else if (item.name === "FINANCE") color = "#f59e0b";
           else if (item.name === "SETF") color = "#8b5cf6";
           else color = "#64748b";
       }
       
       if (showBudget) {
           rawDatasets.push({
               label: item.name + " (Budget)",
               data: item.budget,
               backgroundColor: color,
               borderColor: setfShadeColor(color, -20),
               borderWidth: 1,
               stack: "StackBudget",
               barPercentage: 0.8,
               categoryPercentage: 0.8
           });
       }
       
       if (showActual) {
           rawDatasets.push({
               label: item.name + " (Actual)",
               data: item.realisasi,
               backgroundColor: typeof pattern !== 'undefined' ? pattern.draw(shape, color) : color,
               borderColor: setfShadeColor(color, -20),
               borderWidth: 1,
               stack: "StackRealisasi",
               barPercentage: 0.8,
               categoryPercentage: 0.8
           });
       }
    });

    let scalesCfg = {
        x: {
            stacked: true,
            ticks: { color: textColor, padding: 20 },
            grid: { color: gridColor, display: false }
        },
        y: {
            type: 'linear', display: true, position: 'left',
            stacked: true,
            ticks: { color: textColor, callback: function (value) { return setfFmtJutaan(value); } },
            grid: { color: gridColor }
        }
    };

    const dual = setfInjectDualYAxis(years, rawDatasets, scalesCfg);
    if (dual.scales['y-right']) dual.scales['y-right'].stacked = true;

    setfCharts[canvasId] = new Chart(ctx, {
        type: "bar",
        data: { labels: dual.labels, datasets: dual.datasets },
        plugins: [ChartDataLabels, setfStackTotalPlugin, setfTotalZonePlugin],
        options: {
            responsive: true,
            layout: { padding: { top: 20, bottom: 25 } },
            onClick: function (evt, elements) {
                if (!elements.length) return;
                const idx = elements[0].index;
                const clickedLabel = dual.labels[idx];
                if (clickedLabel !== "TOTAL" && canvasId === "chart-kategori") {
                    setfSetKategoriDrilldown(clickedLabel);
                }
            },
            plugins: {
                legend: { 
                   display: true,
                   position: 'top',
                   align: 'end',
                   labels: { 
                       color: textColor, boxWidth: 12,
                       generateLabels: function(chart) {
                           const original = Chart.defaults.plugins.legend.labels.generateLabels(chart);
                           let unique = [];
                           let seen = new Set();
                           original.forEach(function(item) {
                               if (item.text.includes('(Shadow)')) return;
                               const baseName = item.text.replace(" (Budget)", "").replace(" (Actual)", "");
                               if (!seen.has(baseName)) {
                                   seen.add(baseName);
                                   let newItem = Object.assign({}, item);
                                   newItem.text = baseName;
                                   newItem.datasetIndex = item.datasetIndex;
                                   unique.push(newItem);
                               }
                           });
                           return unique;
                       }
                   },
                   onClick: function(e, legendItem, legend) {
                       const index = legendItem.datasetIndex;
                       const ci = legend.chart;
                       const baseName = legendItem.text;
                       ci.data.datasets.forEach(function(ds, i) {
                           const dsBase = ds.label.replace(" (Budget)", "").replace(" (Actual)", "").replace(" (Shadow)", "");
                           if (dsBase === baseName) {
                               const meta = ci.getDatasetMeta(i);
                               meta.hidden = meta.hidden === null ? !ci.data.datasets[i].hidden : null;
                           }
                       });
                       ci.update();
                   }
                },
                datalabels: { display: false }
            },
            scales: dual.scales
        }
    });
}

function setfInjectDualYAxis(labels, rawDatasets, baseScales) {
    if (!labels || !labels.length) return { labels: [], datasets: rawDatasets, scales: baseScales };
    let newLabels = [...labels, "TOTAL"];
    let newDatasets = [];
    
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#475569";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";
    
    let totalBgt = 0;
    let totalAct = 0;
    
    rawDatasets.forEach(ds => {
        let newData = [...ds.data, 0]; 
        let shadowData = new Array(labels.length + 1).fill(0);
        
        if (ds.stack === "StackBudget") {
            const sum = ds.data.reduce((a, b) => a + (b||0), 0);
            shadowData[labels.length] = sum;
            totalBgt += sum;
        } else if (ds.stack === "StackRealisasi") {
            const sum = ds.data.reduce((a, b) => a + (b||0), 0);
            shadowData[labels.length] = sum;
            totalAct += sum;
        }
        
        ds.data = newData;
        ds.yAxisID = 'y';
        newDatasets.push(ds);
        
        let shadow = Object.assign({}, ds);
        shadow.data = shadowData;
        shadow.yAxisID = 'y-right';
        shadow.label = ds.label + " (Shadow)";
        shadow.backgroundColor = "transparent";
        shadow.borderColor = "transparent";
        if (typeof pattern !== 'undefined' && shadow.backgroundColor && shadow.backgroundColor.draw) {
            shadow.backgroundColor = "transparent"; 
        }
        newDatasets.push(shadow);
    });
    
    let yRight = {
        type: 'linear', display: true, position: 'right',
        stacked: true,
        ticks: { color: textColor, callback: function (value) { return setfFmtJutaan(value); } },
        grid: { drawOnChartArea: false, color: gridColor }
    };
    
    let maxLeft = Math.max(totalBgt, totalAct) * 1.1;
    baseScales['y'].max = maxLeft;
    yRight.max = maxLeft;
    
    baseScales['y-right'] = yRight;
    
    return { labels: newLabels, datasets: newDatasets, scales: baseScales };
}


function setfRenderFamilyTable(families) {
    const tbody = document.querySelector("#setf-family-table tbody");
    if (!tbody) return;
    if (!families || !families.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Belum ada data sahabat.</td></tr>';
      return;
    }
    tbody.innerHTML = families.map(function (f) {
      const memberRows = f.members.map(function (m) {
        const bgt = m.budget || 0;
        const sisa = bgt - m.realisasi;
        return "<tr><td>" + f.label + "</td><td>" + m.nama + "</td>" +
          "<td>" + setfCatBadgeList(m.kategori) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(bgt) + "</td>" +
          '<td class="num-right">' + setfFmtJutaan(m.realisasi) + "</td>" +
          setfSisaCell(sisa) + "</tr>";
      }).join("");
      
      const totalBudget = f.total_budget || f.members.reduce((a,b)=>a+(b.budget||0), 0);
      const totalSisa = totalBudget - f.total_realisasi;
      const totalRow = "<tr style=\"font-weight:bold\"><td>" + f.label + " - Total</td><td></td><td></td>" +
        '<td class="num-right">' + setfFmtJutaan(totalBudget) + "</td>" +
        '<td class="num-right">' + setfFmtJutaan(f.total_realisasi) + "</td>" +
        setfSisaCell(totalSisa) + "</tr>";
      return memberRows + totalRow;
    }).join("");
}


async function setfExportPdf() {
    showToast("Mempersiapkan PDF... Mohon tunggu.", "info");

    if (typeof html2pdf === 'undefined') {
        await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    const container = document.createElement("div");
    container.style.position = "absolute";
    container.style.left = "-9999px";
    container.style.top = "-9999px";
    container.style.width = "1122px";
    container.style.background = "#ffffff";
    document.body.appendChild(container);

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#e2e8f0" : "#1e293b";
    const bgColor = isDark ? "#0f172a" : "#ffffff";
    const borderColor = isDark ? "#334155" : "#e2e8f0";

    const pairs = [
        { title: "Budget vs Actual per Kategori", chart: "chart-kategori", table: "setf-kategori-table" },
        { title: "Budget vs Actual per Pillar", chart: "chart-pillar", table: "setf-pillar-table" },
        { title: "Trend per Tahun per Kategori", chart: "chart-tahunan-kategori", table: "setf-tahunan-kategori-table" },
        { title: "Trend per Tahun per Pillar", chart: "chart-tahunan-pillar", table: "setf-tahunan-pillar-table" },
        { title: "Budget vs Actual per Sahabat", chart: "chart-keluarga", table: "setf-family-table" }
    ];

    pairs.forEach((pair, idx) => {
        const page = document.createElement("div");
        page.style.width = "1122px";
        page.style.height = "790px";
        page.style.padding = "40px";
        page.style.boxSizing = "border-box";
        page.style.display = "flex";
        page.style.flexDirection = "column";
        page.style.background = bgColor;
        page.style.color = textColor;
        
        if (idx < pairs.length - 1) {
            page.style.pageBreakAfter = "always";
        }

        const title = document.createElement("h2");
        title.innerText = pair.title;
        title.style.margin = "0 0 20px 0";
        title.style.fontFamily = "sans-serif";
        title.style.fontSize = "24px";
        page.appendChild(title);

        const content = document.createElement("div");
        content.style.display = "flex";
        content.style.flex = "1";
        content.style.gap = "20px";

        const chartSide = document.createElement("div");
        chartSide.style.flex = "0 0 73%";
        chartSide.style.display = "flex";
        chartSide.style.alignItems = "center";
        chartSide.style.justifyContent = "center";

        if (setfCharts[pair.chart]) {
            const chart = setfCharts[pair.chart];
            const parent = chart.canvas.parentNode;
            
            // Backup original state
            const origWidth = parent.style.width;
            const origHeight = parent.style.height;
            const origPos = parent.style.position;
            const origMaxWidth = parent.style.maxWidth;
            const origAspectRatio = chart.options.maintainAspectRatio;
            const origPixelRatio = chart.options.devicePixelRatio;
            const origAnimation = chart.options.animation;

            // Virtual layout configuration
            parent.style.position = "absolute";
            parent.style.maxWidth = "none";
            parent.style.width = "850px"; 
            parent.style.height = "500px";
            chart.options.maintainAspectRatio = false;
            chart.options.devicePixelRatio = 3; 
            chart.options.animation = false;
            
            // Apply layout changes SYNCHRONOUSLY
            chart.resize();
            chart.update('none');
            
            const img = document.createElement("img");
            img.src = chart.toBase64Image();
            
            // Restore original state
            parent.style.position = origPos;
            parent.style.maxWidth = origMaxWidth;
            parent.style.width = origWidth;
            parent.style.height = origHeight;
            chart.options.maintainAspectRatio = origAspectRatio !== undefined ? origAspectRatio : true;
            chart.options.devicePixelRatio = origPixelRatio || window.devicePixelRatio;
            chart.options.animation = origAnimation;
            
            // Apply original state SYNCHRONOUSLY
            chart.resize();
            chart.update('none');

            img.style.maxWidth = "100%";
            img.style.maxHeight = "100%";
            img.style.objectFit = "contain";
            chartSide.appendChild(img);
        }

        const tableSide = document.createElement("div");
        tableSide.style.flex = "0 0 25%";
        tableSide.style.overflow = "hidden";

        const originalTable = document.getElementById(pair.table);
        if (originalTable) {
            const tableClone = originalTable.cloneNode(true);
            tableClone.style.width = "100%";
            tableClone.style.borderCollapse = "collapse";
            tableClone.style.fontSize = "11px";
            tableClone.style.fontFamily = "sans-serif";
            
            const cells = tableClone.querySelectorAll("th, td");
            cells.forEach(cell => {
                cell.style.padding = "6px";
                cell.style.borderBottom = "1px solid " + borderColor;
                cell.style.color = textColor;
                if (cell.tagName === "TH") {
                    cell.style.textAlign = "left";
                    cell.style.fontWeight = "bold";
                    cell.style.background = isDark ? "#1e293b" : "#f8fafc";
                }
            });
            
            tableSide.appendChild(tableClone);
        }

        content.appendChild(chartSide);
        content.appendChild(tableSide);
        page.appendChild(content);
        container.appendChild(page);
    });

    const opt = {
        margin:       0,
        filename:     'Sahabat_ETF_Dashboard.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, logging: false },
        jsPDF:        { unit: 'pt', format: 'a4', orientation: 'landscape' }
    };

    html2pdf().set(opt).from(container).save().then(() => {
        document.body.removeChild(container);
        showToast("PDF berhasil diunduh!", "success");
    }).catch(err => {
        console.error(err);
        document.body.removeChild(container);
        showToast("Terjadi kesalahan saat membuat PDF.", "error");
    });
}

function setfApplyFilters() {
  const filters = setfGetSelectedFilters();
  const qs = setfBuildQueryString(filters);
  setfUpdateExportLinks(qs);

  setfActiveKategoriDrilldown = null;
  setfRenderDrilldownChip();

  setfRenderSummarySkeleton();
  document.querySelector("#setf-table tbody").innerHTML = skeletonRows(8, 6);
  document.querySelector("#setf-kategori-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-latest-payments-table tbody").innerHTML = skeletonRows(5, 6);
  document.querySelector("#setf-pillar-table tbody").innerHTML = skeletonRows(4, 4);
  document.querySelector("#setf-family-table tbody").innerHTML = skeletonRows(4, 6);
  const tkat = document.querySelector("#setf-tahunan-kategori-table tbody");
  if(tkat) tkat.innerHTML = skeletonRows(3, 4);
  const tpil = document.querySelector("#setf-tahunan-pillar-table tbody");
  if(tpil) tpil.innerHTML = skeletonRows(3, 4);

  setfRefetchLatestPayments();

  fetch("/beasiswa/sahabat/api/family_summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfFamilyData = data;
      try { setfRenderKeluargaChart(); } catch(e) { alert("Err Keluarga Chart: " + e.message); }
      try { setfRenderFamilyTable(data.families); } catch(e) { alert("Err Keluarga Table: " + e.message); }
    })
    .catch(function () { showToast("Gagal memuat data sahabat.", "error"); });

  fetch("/beasiswa/sahabat/api/summary" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      setfRenderSummaryCards(data.rows);
      setfRenderTable(data.rows);
    })
    .catch(function () { showToast("Gagal memuat ringkasan anggota.", "error"); });

  fetch("/beasiswa/sahabat/api/breakdown" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      try { setfRenderKategoriChartCustom("chart-kategori", data.kategori); } catch(e) { alert("Err Kategori Chart: " + e.message); }
      try { setfRenderKategoriTable(data.kategori); } catch(e) { alert("Err Kategori Table: " + e.message); }
      try { setfRenderAlert(data.over_budget); } catch(e) { alert("Err Alert: " + e.message); }
      try { setfRenderTahunanData(data.yearly); } catch(e) { alert("Err Tahunan Data: " + e.message); }
      try { setfRenderPillarTable(data.pillar); } catch(e) { alert("Err Pillar Table: " + e.message); }
      try { setfRenderCustomBudgetChart("chart-pillar", data.pillar, "pillar"); } catch(e) { alert("Err Pillar Chart: " + e.message); }
    })
    .catch(function (e) { alert("Fetch failed: " + e.message); showToast("Gagal memuat breakdown kategori.", "error"); });

  if (filters.years.length) {
    document.querySelector("#setf-monthly-table tbody").innerHTML = skeletonRows(2, 4);
    fetch("/beasiswa/sahabat/api/monthly?" + qs)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        setfRenderMonthlyChart(data.months);
        setfRenderMonthlyTable(data.comparison, filters.years);
      })
      .catch(function () { showToast("Gagal memuat data bulanan.", "error"); });
  } else {
    if (setfCharts["chart-bulanan"]) { setfCharts["chart-bulanan"].destroy(); delete setfCharts["chart-bulanan"]; }
    setfRenderMonthlyTable([], []);
  }
}

function initSetfSubtabs() {
  const buttons = document.querySelectorAll(".setf-subtab-btn");
  const panels = document.querySelectorAll(".setf-subtab-panel");
  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      buttons.forEach(function (b) { b.classList.remove("active"); });
      panels.forEach(function (p) { p.classList.remove("active"); });
      btn.classList.add("active");
      const panel = document.getElementById("setf-subtab-" + btn.dataset.subtab);
      if (panel) panel.classList.add("active");
      if (btn.dataset.subtab === "laporan" && !window._setfLaporanLoaded) {
        window._setfLaporanLoaded = true;
        setfLoadLaporan();
      }
      if (btn.dataset.subtab === "treequery") { initTreeQuery(); }
      if (btn.dataset.subtab === "detail" && !window._setfDetailLoaded) {
        window._setfDetailLoaded = true;
        setfLoadDetailTransaksi();
      }
      if (btn.dataset.subtab === "pohon" && !window._setfPohonLoaded) {
        window._setfPohonLoaded = true;
        setfLoadPohon();
      }
    });
  });
}

function initSahabatEtf() {
  // Hanya inisialisasi satu kali — dipanggil dari onclick tombol tab
  // "Sahabat ETF" di Beasiswa setiap kali tab diklik, tidak hanya sekali
  // seperti DOMContentLoaded pada halaman standalone-nya.
  if (window._sahabatInitialized) return;
  window._sahabatInitialized = true;

  initSetfSubtabs();
  // Scoped to each sub-tab's own container — Dashboard and Detail Transaksi
  // each have their own .beasiswa-dash-filter-chip instances (different
  // checkbox classes), so a document-wide call would wire both sets to the
  // same callback.
  initFilterChips(document.getElementById("setf-subtab-dashboard"), setfApplyFilters);
  initFilterChips(document.getElementById("setf-subtab-detail"), setfLoadDetailTransaksi);
  const reportYearSelect = document.getElementById("setf-report-year");
  const reportMonthSelect = document.getElementById("setf-report-month");
  
  function reloadLaporan() {
    setfUpdateReportExportLink();
    if (window._setfLaporanLoaded) setfLoadLaporan();
  }
  
  if (reportYearSelect) {
    reportYearSelect.addEventListener("change", reloadLaporan);
    setfUpdateReportExportLink();
  }
  if (reportMonthSelect) {
    reportMonthSelect.addEventListener("change", reloadLaporan);
  }
  
  const laporanTab = document.getElementById("setf-subtab-laporan");
  if (laporanTab) {
    initFilterChips(laporanTab, reloadLaporan);
  }
  
  const pohonTab = document.getElementById("setf-subtab-pohon");
  if (pohonTab) {
    initFilterChips(pohonTab, function() {
      if (window._setfPohonLoaded) setfLoadPohon();
    });
  }
  const reportPohonMonth = document.getElementById("setf-pohon-month");
  if (reportPohonMonth) {
    reportPohonMonth.addEventListener("change", function() {
      if (window._setfPohonLoaded) setfLoadPohon();
    });
  }
  setfApplyFilters();
}

window.addEventListener("fh-theme-changed", function () {
  if (setfCharts["chart-kategori"] || setfCharts["chart-bulanan"] || setfCharts["chart-tahunan"] || setfCharts["chart-keluarga"]) {
    setfApplyFilters();
  }
});

// ─── Laporan tab: on-screen rendering of the Excel report's data ────────────
function setfLaporanHeaderRow(reportYear) {
  return '<tr class="setf-laporan-header">' +
    '<th rowspan="2">Nama</th><th rowspan="2">Periode</th><th rowspan="2">Pillar</th>' +
    '<th colspan="4">Tahun ' + reportYear + '</th>' +
    '<th colspan="4">S/D Tahun ' + reportYear + '</th></tr>' +
    '<tr class="setf-laporan-header">' +
    '<th>Plafon</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th>' +
    '<th>Plafon</th><th>Klaim</th><th>Dibayar</th><th>Saldo</th></tr>';
}

function setfLaporanMetricsCells(m) {
  return '<td class="num-right">' + setfFmtJutaan(m.cur.plafon) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cur.klaim) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cur.dibayar) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cur.saldo) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.plafon) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.klaim) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.dibayar) + '</td>' +
         '<td class="num-right">' + setfFmtJutaan(m.cum.saldo) + '</td>';
}

function setfLaporanPeriodeText(row) {
  if (!row.periode_start || !row.periode_end) return '';
  return row.periode_start + ' - ' + row.periode_end;
}

function setfLaporanNamaRow(row, cls) {
  return '<tr class="' + cls + '"><td>' + row.nama + '</td><td>' + setfLaporanPeriodeText(row) + '</td><td>' + row.pillar + '</td>' +
    setfLaporanMetricsCells(row) + '</tr>';
}

function setfLaporanLabelRow(label, metrics, cls) {
  return '<tr class="' + cls + '"><td colspan="3">' + label + '</td>' +
    setfLaporanMetricsCells(metrics) + '</tr>';
}

function setfRenderLaporanSection(section, reportYear) {
  let html = '<h4 class="setf-laporan-section-title">' + section.label + '</h4>';
  html += '<table class="setf-laporan-table"><thead>' + setfLaporanHeaderRow(reportYear) + '</thead><tbody>';
  section.groups.forEach(function (group) {
    html += setfLaporanLabelRow(group.label, group.subtotal, 'setf-laporan-subtotal-row');
    group.siswa_rows.forEach(function (row) {
      html += setfLaporanNamaRow(row, 'setf-laporan-siswa-row');
    });
  });
  html += setfLaporanLabelRow('TOTAL ' + section.label, section.total, 'setf-laporan-total-row');
  html += '</tbody></table>';
  if (section.recap.length) {
    html += '<table class="setf-laporan-table setf-laporan-recap">' +
      '<caption>Rekap ' + section.label + '</caption><thead>' + setfLaporanHeaderRow(reportYear) + '</thead><tbody>';
    section.recap.forEach(function (row) {
      html += setfLaporanNamaRow(row, 'setf-laporan-recap-row');
    });
    html += '</tbody></table>';
  }
  return html;
}

function setfRenderLaporanPillarBreakdown(pillarBreakdown, grandTotal, reportYear) {
  let html = '<h4 class="setf-laporan-section-title">Breakdown Pillar</h4>';
  html += '<table class="setf-laporan-table"><thead>' + setfLaporanHeaderRow(reportYear) + '</thead><tbody>';
  html += setfLaporanLabelRow('GRAND TOTAL', grandTotal, 'setf-laporan-total-row');
  pillarBreakdown.forEach(function (p) {
    html += '<tr class="setf-laporan-subtotal-row"><td colspan="3">' + p.pillar_label + '</td>' +
      setfLaporanMetricsCells(p) + '</tr>';
    html += '<tr class="setf-laporan-pct-row"><td colspan="3">% to total</td>' +
      '<td class="num-right">' + (p.pct_cur.plafon * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cur.klaim * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cur.dibayar * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cur.saldo * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.plafon * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.klaim * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.dibayar * 100).toFixed(1) + '%</td>' +
      '<td class="num-right">' + (p.pct_cum.saldo * 100).toFixed(1) + '%</td></tr>';
  });
  html += '</tbody></table>';
  return html;
}

function setfRenderLaporan(data) {
  let html = '<h3>REPORT — Tahun ' + data.report_year + '</h3>';
  data.sections.forEach(function (section) {
    html += setfRenderLaporanSection(section, data.report_year);
  });
  html += '<h4 class="setf-laporan-section-title">Total Pendidikan &amp; Kesehatan</h4>';
  html += '<table class="setf-laporan-table"><thead>' + setfLaporanHeaderRow(data.report_year) + '</thead><tbody>';
  html += setfLaporanLabelRow('TOTAL PENDIDIKAN &amp; KESEHATAN', data.combined_total, 'setf-laporan-total-row');
  data.combined_recap.forEach(function (row) {
    html += setfLaporanNamaRow(row, 'setf-laporan-recap-row');
  });
  html += setfLaporanLabelRow('GRAND TOTAL', data.grand_total, 'setf-laporan-total-row');
  html += '</tbody></table>';
  html += setfRenderLaporanPillarBreakdown(data.pillar_breakdown, data.grand_total, data.report_year);
  document.getElementById('setf-laporan-content').innerHTML = html;
}

function setfLoadLaporan() {
  const sel = document.getElementById('setf-report-year');
  if (!sel) return;
  
  let qs = 'year=' + encodeURIComponent(sel.value);
  const monthSel = document.getElementById('setf-report-month');
  if (monthSel) qs += '&month=' + encodeURIComponent(monthSel.value);
  
  const pillars = Array.from(document.querySelectorAll('.setf-laporan-pillar-cb:checked')).map(function (cb) { return cb.value; });
  pillars.forEach(function (p) { qs += '&pillars[]=' + encodeURIComponent(p); });

  document.getElementById('setf-laporan-content').innerHTML =
    '<p style="color:var(--text-muted);text-align:center;padding:2rem">Memuat laporan...</p>';
  fetch('/beasiswa/sahabat/api/report?' + qs)
    .then(function (r) { return r.json(); })
    .then(function (resp) {
      if (!resp.ok) { showToast(resp.pesan || 'Gagal memuat laporan.', 'error'); return; }
      setfRenderLaporan(resp.data);
    })
    .catch(function () { showToast('Gagal memuat laporan.', 'error'); });
}

// ─── Detail Transaksi tab: full transaction list ────────────────────────────
function setfGetDetailFilters() {
  const years = Array.from(document.querySelectorAll(".setf-detail-year-cb:checked")).map(function (cb) { return cb.value; });
  const pillars = Array.from(document.querySelectorAll(".setf-detail-pillar-cb:checked")).map(function (cb) { return cb.value; });
  return { years: years, pillars: pillars };
}

function setfUpdateDetailExportLink(qs) {
  const link = document.getElementById("setf-export-detail");
  if (!link) return;
  const base = link.href.split("?")[0];
  link.href = qs ? base + "?" + qs : base;
}

function setfRenderDetailTable(rows) {
  const tbody = document.querySelector("#setf-detail-table tbody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted)">Belum ada transaksi.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    return "<tr>" +
      "<td>" + r.sumber + "</td>" +
      "<td>" + r.siswa_code + "</td>" +
      "<td>" + r.nama + "</td>" +
      "<td>" + r.tanggal + "</td>" +
      "<td>" + r.cat1 + "</td>" +
      "<td>" + (r.cat2 || "") + "</td>" +
      '<td class="num-right">' + setfFmtJutaan(r.amount) + "</td>" +
      "<td>" + (r.status || "") + "</td>" +
      "</tr>";
  }).join("");
}

function setfLoadDetailTransaksi() {
  const filters = setfGetDetailFilters();
  const qs = setfBuildQueryString(filters);
  setfUpdateDetailExportLink(qs);
  document.querySelector("#setf-detail-table tbody").innerHTML = skeletonRows(6, 8);
  fetch("/beasiswa/sahabat/api/all_transactions" + (qs ? "?" + qs : ""))
    .then(function (r) { return r.json(); })
    .then(function (resp) {
      if (!resp.ok) { showToast(resp.pesan || "Gagal memuat detail transaksi.", "error"); return; }
      setfRenderDetailTable(resp.rows);
    })
    .catch(function () { showToast("Gagal memuat detail transaksi.", "error"); });
}

// --- Diagram Pohon ---

function setfLoadPohon() {
  const years = Array.from(document.querySelectorAll('.setf-pohon-year-cb:checked')).map(cb => cb.value);
  const selMonth = document.getElementById('setf-pohon-month');
  
  const pillars = Array.from(document.querySelectorAll('.setf-pohon-pillar-cb:checked')).map(cb => cb.value);
  
  let qs = '';
  years.forEach(y => { qs += 'years[]=' + encodeURIComponent(y) + '&'; });
  qs = qs.slice(0, -1);

  if (selMonth) qs += '&month=' + encodeURIComponent(selMonth.value);
  pillars.forEach(p => { qs += '&pillars[]=' + encodeURIComponent(p); });

  const container1 = document.getElementById('setf-pohon-container');
  const container2 = document.getElementById('setf-pohon-group-container');
  
  if (container1) container1.innerHTML = '<div style="text-align:center;color:var(--text-muted)">Memuat data pohon...</div>';
  if (container2) container2.innerHTML = '';

  fetch('/beasiswa/sahabat/api/pohon?' + qs)
    .then(r => r.json())
    .then(resp => {
      if (!resp.ok) {
        showToast(resp.pesan || 'Gagal memuat diagram pohon.', 'error');
        return;
      }
      window._setfPohonLoaded = true;
      if (container1) container1.innerHTML = setfRenderDiagram1(resp.data.diagram1);
      if (container2) container2.innerHTML = setfRenderDiagram2(resp.data.diagram2);
    })
    .catch(e => {
      showToast('Gagal memuat diagram pohon.', 'error');
    });
}

function setfBuildTreeNode(nodeData, isGroupNode=false) {
  const widthClass = isGroupNode ? 'tree-node-group' : '';
  const label = nodeData.label || nodeData.group_name;
  
  let html = `
    <div class="tree-node ${widthClass}" style="margin: 0 auto;">
      <div class="tree-node-header">${label}</div>
      <div class="tree-node-body">
        <div class="tree-metrics">
          <div class="tree-metric-box">
            <div class="tree-metric-label">Plafon</div>
            <div class="tree-metric-val">${setfFmtJutaan(nodeData.plafon)}</div>
          </div>
          <div class="tree-metric-box">
            <div class="tree-metric-label">Realisasi</div>
            <div class="tree-metric-val">${setfFmtJutaan(nodeData.realisasi)}</div>
          </div>
        </div>
  `;
  
  const list = nodeData.siswa || nodeData.detail || [];
  if (list.length > 0) {
    html += `
        <div class="tree-table-wrap">
          <table class="tree-table">
            <thead>
              <tr>
                <th>Nama</th>
                <th style="text-align:right">Plafon</th>
                <th style="text-align:right">Realisasi</th>
              </tr>
            </thead>
            <tbody>
    `;
    let totPlafon = 0;
    let totRealisasi = 0;
    list.forEach(item => {
      totPlafon += item.plafon || 0;
      totRealisasi += item.realisasi || 0;
      html += `
              <tr>
                <td>${item.nama}</td>
                <td>${setfFmtJutaan(item.plafon)}</td>
                <td>${setfFmtJutaan(item.realisasi)}</td>
              </tr>
      `;
    });
    html += `
              <tr class="tree-total-row">
                <td>Total</td>
                <td>${setfFmtJutaan(totPlafon)}</td>
                <td>${setfFmtJutaan(totRealisasi)}</td>
              </tr>
            </tbody>
          </table>
        </div>
    `;
  }
  
  html += `
      </div>
    </div>
  `;
  return html;
}

function setfRenderDiagram1(data) {
  if (!data || !data.root) return '<div style="color:var(--text-muted)">Data kosong</div>';
  
  return `
    <style>
      .setf-tree-branch { display: flex; gap: 1.5rem; padding-top: 20px; position: relative; }
      .setf-tree-branch .tree-item { position: relative; display: flex; flex-direction: column; align-items: center; }
      .setf-tree-branch .tree-item::before { content:""; position:absolute; top: -20px; left: 50%; width: 2px; height: 20px; background: var(--accent); }
      .setf-tree-branch .tree-item::after { content:""; position:absolute; top: -20px; height: 2px; background: var(--accent); }
      .setf-tree-branch .tree-item:first-child::after { left: 50%; right: -0.75rem; }
      .setf-tree-branch .tree-item:last-child::after { right: 50%; left: -0.75rem; }
      .setf-tree-branch .tree-item:not(:first-child):not(:last-child)::after { left: -0.75rem; right: -0.75rem; }
      .setf-tree-branch .tree-item:first-child:last-child::after { display: none; }
      
      /* Print scale so the tree structure fits on A4 Landscape */
      @media print {
        #setf-pohon-group-container > div { zoom: 0.55; }
        #setf-pohon-container > div { zoom: 0.8; }
      }
    </style>
    <div style="display:flex; flex-direction:column; align-items:center; min-width: max-content; padding: 10px;">
      ${setfBuildTreeNode(data.root)}
      
      <div class="tree-connector-root" style="width: 2px; height: 20px; background: var(--accent);"></div>
      
      <div class="setf-tree-branch">
        <div class="tree-item">${setfBuildTreeNode(data.kesehatan)}</div>
        <div class="tree-item">${setfBuildTreeNode(data.pendidikan)}</div>
      </div>
    </div>
  `;
}

function setfRenderDiagram2(data) {
  if (!data || !data.root || !data.groups) return '';
  
  let groupsHtml = data.groups.map(g => `
    <div class="tree-item">
      ${setfBuildTreeNode(g, true)}
    </div>
  `).join('');
  
  return `
    <div style="display:flex; flex-direction:column; align-items:center; min-width: max-content; padding: 10px;">
      ${setfBuildTreeNode(data.root)}
      
      <div class="tree-connector-root" style="width: 2px; height: 20px; background: var(--accent);"></div>
      
      <div class="setf-tree-branch">
        ${groupsHtml}
      </div>
    </div>
  `;
}

let treeChartInstance = null;
let treeRawData = null;


function assignGenerations(node, depth) {
  if (depth > 1) {
    node.genLabel = "L" + (depth - 1);
  } else {
    node.genLabel = "";
  }
  if (node.children) {
    node.children.forEach(c => assignGenerations(c, depth + 1));
  }
}

async function initTreeQuery() {
  if (treeChartInstance) return;
  const chartDom = document.getElementById("tree-chart");
  if (!chartDom) return;
  
  treeChartInstance = echarts.init(chartDom);
  const searchInput = document.getElementById('tree-search-input');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') searchTree();
    });
  }
  treeChartInstance.showLoading();
  
  try {
    const res = await fetch("/beasiswa/sahabat/tree-data");
    const json = await res.json();
    if (!json.ok) throw new Error("Gagal ambil data");
    
        treeRawData = {
      name: "Sahabat ETF",
      children: json.data
    };
    assignGenerations(treeRawData, 0);
      assignUID(treeRawData);
      applyInitialDepth(treeRawData, 0, 2);
      window.treeRawDataPristine = JSON.parse(JSON.stringify(treeRawData));
      
    const dl = document.getElementById("tree-search-list");
    if (dl) {
      let opts = [];
      function collectNames(n) {
         opts.push(`<option value="${n.name}">`);
         if (n.partners) n.partners.forEach(p => opts.push(`<option value="${p.name}">`));
         if (n.children) n.children.forEach(c => collectNames(c));
      }
      if (window.treeRawDataPristine.children) window.treeRawDataPristine.children.forEach(c => collectNames(c));
      dl.innerHTML = opts.join("");
    }
    renderTree([treeRawData]);
  } catch (err) {
    console.error(err);
  } finally {
    treeChartInstance.hideLoading();
  }
}

function renderTree(data) {
    window.currentTreeData = data;
    let leaves = countVisibleLeaves(data[0]);
    let maxDepth = getVisibleDepth(data[0], 0);
    let wrapper = document.getElementById("tree-wrapper");
    let baseW = wrapper ? wrapper.clientWidth : 1200;
    let baseH = wrapper ? wrapper.clientHeight : 800;
    if (baseH < 600) baseH = 600;
    
    let newWidth = Math.max(baseW, leaves * 140) * (window.treeSpacingMultiplier || 1.0);
    let newHeight = Math.max(baseH, (maxDepth + 1) * 320) * (window.treeSpacingMultiplier || 1.0);
    
    let chartDiv = document.getElementById("tree-chart");
    if (chartDiv) {
        chartDiv.style.width = newWidth + "px";
        chartDiv.style.height = newHeight + "px";
        if (treeChartInstance) treeChartInstance.resize();
    }
  const option = {
    tooltip: { 
      trigger: 'item', 
      triggerOn: 'mousemove',
      formatter: function(params) {
         let d = params.data;
         if (!d) return '';
         let mainIdStr = d.id ? ' | ' + d.id : '';
           let html = '<div style=\"font-weight:bold;margin-bottom:5px;border-bottom:1px solid #eee;padding-bottom:3px;\">' + (d.name || '') + mainIdStr + '</div>';
         
         let hasInfo = false;
         if (d.tanggal_lahir) { html += '<div style="font-size:12px;"><b>Tanggal Lahir:</b> ' + d.tanggal_lahir + '</div>'; hasInfo = true; }
         if (d.catatan) { html += '<div style="font-size:12px;max-width:250px;white-space:normal;"><b>Catatan:</b> ' + d.catatan + '</div>'; hasInfo = true; }
         if (!hasInfo) { html += '<div style="font-size:12px;color:#888;"><i>Tidak ada informasi tambahan</i></div>'; }
         
         if (d.partners && d.partners.length > 0) {
             html += '<hr style="margin:8px 0; border:0; border-top:1px solid #ddd">';
             d.partners.forEach(p => {
                 let pIdStr = p.id ? ' | ' + p.id : '';
                   html += '<div style=\"font-weight:bold;margin-bottom:3px;\">' + (p.name || '') + ' <span style=\"font-size:11px;color:#666;font-weight:normal;\">(Partner)</span>' + pIdStr + '</div>';
                 let hasPInfo = false;
                 if (p.tanggal_lahir) { html += '<div style="font-size:12px;"><b>Tanggal Lahir:</b> ' + p.tanggal_lahir + '</div>'; hasPInfo = true; }
                 if (p.catatan) { html += '<div style="font-size:12px;max-width:250px;white-space:normal;"><b>Catatan:</b> ' + p.catatan + '</div>'; hasPInfo = true; }
                 if (!hasPInfo) { html += '<div style="font-size:12px;color:#888;"><i>Tidak ada informasi tambahan</i></div>'; }
             });
         }
         return html;
      }
    },
    series: [
      {
        type: 'tree',
        orient: 'TB',
        edgeShape: 'polyline',
        data: data,
        top: 80, left: 20, bottom: 80, right: 20,
        symbolSize: 7,
        roam: true,
        label: {
          position: 'top',
          verticalAlign: 'middle',
          align: 'center',
          fontSize: 12,
          backgroundColor: '#f8f9fa',
          borderColor: '#d1d5db',
          borderWidth: 1,
          borderRadius: 4,
          padding: 6,
          
                    formatter: function(params) {
            function wrapText(str, maxLen) {
                if (!str) return [''];
                let words = str.split(' ');
                let outLines = [];
                let currentLine = '';
                for (let word of words) {
                    if (currentLine.length + word.length > maxLen && currentLine.length > 0) {
                        outLines.push(currentLine.trim());
                        currentLine = word + ' ';
                    } else {
                        currentLine += word + ' ';
                    }
                }
                if (currentLine.trim()) outLines.push(currentLine.trim());
                return outLines.length > 0 ? outLines : [''];
            }

            let n = params.data.name || '';
            let lastCode = params.data.id ? params.data.id.split('.').pop() : '';
            if (lastCode && lastCode !== 'A' && lastCode !== 'B') {
                n = n + ' (' + lastCode + ')';
            }
            
            let gen = params.data.genLabel ? `{gen|[${params.data.genLabel}]} ` : '';
            let lines = [];
            let wrappedMain = wrapText(n, 15);
            wrappedMain.forEach((w, idx) => {
                if (idx === 0) lines.push(`${gen}{main|${w}}`);
                else lines.push(`{main|${w}}`);
            });
            
            let ps = params.data.partners;
            if (ps && ps.length > 0) {
                lines.push('{sep|---------------}');
                ps.forEach(p => {
                    let pCode = p.id ? p.id.split('.').pop() : '';
                    let pName = p.name || '';
                    if (pCode && pCode !== 'A' && pCode !== 'B') {
                        pName = pName + ' (' + pCode + ')';
                    }
                    pName = pName + ' (Partner)';
                    let wrappedPartner = wrapText(pName, 20);
                    wrappedPartner.forEach(w => {
                        lines.push(`{partner|${w}}`); 
                    });
                });
            }
            
            return lines.join('\n');
          },
          rich: {
            main: { fontWeight: 'bold', fontSize: 13, padding: [4,0,4,0] },
            gen: { fontSize: 11, color: '#3b82f6', fontWeight: 'bold' },
            sep: { color: '#ccc', height: 2 },
            partner: { fontSize: 11, color: '#666', padding: [2,0,2,0] }
          }
        },
        leaves: { label: { position: 'bottom', verticalAlign: 'middle', align: 'center' } },
        emphasis: { focus: 'descendant' },
        expandAndCollapse: true,
        animationDuration: 550,
        animationDurationUpdate: 750
      }
    ]
  };
  treeChartInstance.setOption(option);
    
    treeChartInstance.off('click');
    treeChartInstance.on('click', function(e) {
        if (!e.data || !e.data._uid) return;
        
        let targetUid = e.data._uid;
        
        function findParentUid(node, targetId, parentId) {
            if (node._uid === targetId) return parentId;
            if (node.children) {
                for (let i = 0; i < node.children.length; i++) {
                    let pid = findParentUid(node.children[i], targetId, node._uid);
                    if (pid) return pid;
                }
            }
            return null;
        }
        
        if (window.currentDrillTargetUid === targetUid) {
            let parentUid = findParentUid(window.treeRawDataPristine, targetUid, null);
            if (parentUid) {
                targetUid = parentUid;
            } else {
                resetTreeQuery();
                window.currentDrillTargetUid = null;
                return;
            }
        }
        window.currentDrillTargetUid = targetUid;
        
        let dataCopy = JSON.parse(JSON.stringify(window.treeRawDataPristine));
        
        function drillDownToUid(node, targetId) {
            if (node._uid === targetId) {
                node.collapsed = false;
                return true;
            }
            
            let foundChild = null;
            if (node.children) {
                for (let i = 0; i < node.children.length; i++) {
                    let c = node.children[i];
                    if (drillDownToUid(c, targetId)) {
                        foundChild = c;
                        break;
                    }
                }
            }
            
            if (foundChild) {
                node.children = [foundChild];
                node.collapsed = false;
                return true;
            }
            return false;
        }
        
        if (drillDownToUid(dataCopy, targetUid)) {
            window.currentTreeData = [dataCopy];
            let leaves = countVisibleLeaves(window.currentTreeData[0]);
            let maxDepth = getVisibleDepth(window.currentTreeData[0], 0);
            
            let wrap = document.getElementById("tree-wrapper");
            let baseW = wrap ? wrap.clientWidth : 1200;
            let baseH = wrap ? wrap.clientHeight : 800;
            if (baseH < 600) baseH = 600;
            
            let newWidth = Math.max(baseW, leaves * 140) * (window.treeSpacingMultiplier || 1.0);
            let newHeight = Math.max(baseH, (maxDepth + 1) * 320) * (window.treeSpacingMultiplier || 1.0);
            
            let cDiv = document.getElementById('tree-chart');
            if (cDiv.style.width !== newWidth + 'px' || cDiv.style.height !== newHeight + 'px') {
                cDiv.style.width = newWidth + 'px';
                cDiv.style.height = newHeight + 'px';
                treeChartInstance.resize();
            }
            
            treeChartInstance.setOption({
                series: [{ data: window.currentTreeData }]
            });
        }
    });

    setTimeout(() => {
        const wrapper = document.getElementById("tree-wrapper");
        if (wrapper) {
            wrapper.scrollLeft = (wrapper.scrollWidth - wrapper.clientWidth) / 2;
        }
    }, 100);
  }

function expandPathToName(node, searchName) {
  let found = false;
  let isTarget = false;

  if (node.name.toLowerCase().includes(searchName)) {
    found = true;
    isTarget = true;
  }
  if (node.partners && node.partners.some(p => p.name.toLowerCase().includes(searchName))) {
    found = true;
    isTarget = true;
  }

  let matchedChildren = [];
  let neededPartnerIds = new Set();
  let hasTargetChild = false;

  if (node.children && node.children.length > 0) {
    node.children.forEach(c => {
      let isChildTarget = (c.name.toLowerCase().includes(searchName) || 
                          (c.partners && c.partners.some(p => p.name.toLowerCase().includes(searchName))));
      if (isChildTarget) {
          hasTargetChild = true;
      }
      if (expandPathToName(c, searchName)) {
        matchedChildren.push(c);
        if (c.parent_partner_id) {
          neededPartnerIds.add(c.parent_partner_id);
        }
        found = true;
      }
    });
  }

  if (found && !isTarget) {
    let arr = Array.from(neededPartnerIds);
    if (hasTargetChild) {
        node.children = node.children.filter(c => c.parent_partner_id && arr.includes(c.parent_partner_id));
        if (node.partners) {
           node.partners = node.partners.filter(p => arr.includes(p.id));
        }
        node.collapsed = false;
    } else {
        node.children = matchedChildren;
        if (node.partners) {
           node.partners = node.partners.filter(p => arr.includes(p.id));
        }
        node.collapsed = false;
    }
  } else if (isTarget) {
    node.collapsed = false; 
    node.itemStyle = { borderColor: '#ef4444', borderWidth: 3 };
    node.label = { backgroundColor: '#fee2e2', borderColor: '#ef4444' };
  } else {
    node.collapsed = true;
  }
  return found;
}

function searchTree() {
    window.currentDrillTargetUid = null;
    const input = document.getElementById("tree-search-input");
    const q = input ? input.value.toLowerCase() : "";
    let dataCopy = JSON.parse(JSON.stringify(window.treeRawDataPristine));
    
    if (!q) {
        renderTree([dataCopy]);
        return;
    }
    
    expandPathToName(dataCopy, q);
    if (dataCopy.children && dataCopy.children.length === 1) {
        renderTree([dataCopy.children[0]]);
    } else {
        renderTree([dataCopy]);
    }
  }


  function adjustSpacing(delta) {
      if (!window.currentTreeData) return;
      window.treeSpacingMultiplier += delta;
      if (window.treeSpacingMultiplier < 0.3) window.treeSpacingMultiplier = 0.3;
      if (window.treeSpacingMultiplier > 5.0) window.treeSpacingMultiplier = 5.0;
      
      let leaves = countVisibleLeaves(window.currentTreeData[0]);
      let maxDepth = getVisibleDepth(window.currentTreeData[0], 0);
      
      let wrap = document.getElementById("tree-wrapper");
      let baseW = wrap ? wrap.clientWidth : 1200;
      let baseH = wrap ? wrap.clientHeight : 800;
      if (baseH < 600) baseH = 600;
      
      let newWidth = Math.max(baseW, leaves * 140) * window.treeSpacingMultiplier;
      let newHeight = Math.max(baseH, (maxDepth + 1) * 320) * window.treeSpacingMultiplier;
      
      let chartDiv = document.getElementById("tree-chart");
      if (chartDiv) {
          chartDiv.style.width = newWidth + "px";
          chartDiv.style.height = newHeight + "px";
      }
      if (treeChartInstance) {
          treeChartInstance.resize();
      }
  }

function zoomTreeQuery(ratio) {
      if (treeChartInstance) {
          treeChartInstance.dispatchAction({
              type: 'treeRoam',
              zoom: ratio
          });
      }
    }
  function foldChildren(node, depth) {
    // If it's Depth 2 (Wives) and it's not part of an expanded search path
    if (depth === 2 && node.collapsed !== false && node.children && node.children.length > 0) {
      node._folded = true;
      node._actualChildren = node.children;
      node.children = []; // Remove children so they don't branch
    } else if (node.children) {
      node.children.forEach(c => foldChildren(c, depth + 1));
    }
  }

  function resetTreeQuery() {
    window.treeSpacingMultiplier = 1.0;
    window.currentDrillTargetUid = null;
    const input = document.getElementById("tree-search-input");
    if (input) input.value = "";
    searchTree();
  }

  async function exportTreePDF() {
    if (!treeChartInstance) return;
    showToast("Mempersiapkan PDF... Memotong area kosong agar maksimal.", "info");
    
    if (typeof html2pdf === 'undefined') {
        await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    let rawImgData = treeChartInstance.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#fff'
    });
    
    // Helper to crop whitespace
    function cropWhitespace(dataUrl) {
        return new Promise((resolve) => {
            let img = new Image();
            img.onload = () => {
                let canvas = document.createElement('canvas');
                let ctx = canvas.getContext('2d');
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
                
                let imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                let data = imgData.data;
                
                let top = null, bottom = null, left = null, right = null;
                
                for (let y = 0; y < canvas.height; y++) {
                    for (let x = 0; x < canvas.width; x++) {
                        let alpha = data[(y * canvas.width + x) * 4 + 3];
                        let r = data[(y * canvas.width + x) * 4];
                        let g = data[(y * canvas.width + x) * 4 + 1];
                        let b = data[(y * canvas.width + x) * 4 + 2];
                        
                        // Check if pixel is NOT white (#ffffff)
                        if (alpha > 0 && (r < 254 || g < 254 || b < 254)) {
                            if (top === null) top = y;
                            bottom = y;
                            if (left === null || x < left) left = x;
                            if (right === null || x > right) right = x;
                        }
                    }
                }
                
                if (top === null) {
                    resolve(dataUrl);
                    return;
                }
                
                // 40px padding
                let padding = 40;
                top = Math.max(0, top - padding);
                bottom = Math.min(canvas.height, bottom + padding);
                left = Math.max(0, left - padding);
                right = Math.min(canvas.width, right + padding);
                
                let width = right - left;
                let height = bottom - top;
                
                let cropCanvas = document.createElement('canvas');
                cropCanvas.width = width;
                cropCanvas.height = height;
                let cropCtx = cropCanvas.getContext('2d');
                
                cropCtx.fillStyle = '#ffffff';
                cropCtx.fillRect(0, 0, width, height);
                cropCtx.drawImage(canvas, left, top, width, height, 0, 0, width, height);
                
                resolve(cropCanvas.toDataURL('image/jpeg', 1.0));
            };
            img.src = dataUrl;
        });
    }

    let imgData = await cropWhitespace(rawImgData);

    let opt = {
        margin:       10,
        filename:     'Sahabat_ETF_Tree.pdf',
        image:        { type: 'jpeg', quality: 1.0 },
        html2canvas:  { scale: 2 },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'landscape' }
    };
    
    let img = new Image();
    img.onload = function() {
        if (img.height > img.width) {
            opt.jsPDF.orientation = 'portrait';
        }
        
        let container = document.createElement('div');
        container.style.width = '100%';
        container.style.textAlign = 'center';
        
        let pdfImg = document.createElement('img');
        pdfImg.src = imgData;
        pdfImg.style.maxWidth = '100%';
        container.appendChild(pdfImg);
        
        html2pdf().set(opt).from(container).save().then(() => {
            showToast("PDF berhasil diunduh!", "success");
        });
    };
    img.src = imgData;
  }
