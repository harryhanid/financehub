import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'const setfStackTotalPlugin = \{.*?\n  \};'

replacement = """const setfStackTotalPlugin = {
  id: 'customLabels',
  afterDatasetsDraw: function(chart) {
    const ctx = chart.ctx;
    ctx.save();
    
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    ctx.font = 'bold 10px sans-serif';
    ctx.fillStyle = isDark ? "#e2e8f0" : "#475569";
    ctx.textAlign = 'center';
    
    const metaMap = {};
    chart.data.datasets.forEach(function(dataset, i) {
      const meta = chart.getDatasetMeta(i);
      if (!meta.hidden) {
         const stackId = meta.stack || 'default';
         if (!metaMap[stackId]) metaMap[stackId] = [];
         metaMap[stackId].push({ index: i, meta: meta, data: dataset.data });
      }
    });

    const numDataPoints = chart.data.labels.length;
    const yBaseline = chart.scales.y.getPixelForValue(0);

    for (let stackId in metaMap) {
      const layers = metaMap[stackId];
      for (let j = 0; j < numDataPoints; j++) {
        let sum = 0;
        let lastValidMeta = null;
        let anyMeta = null; // To get X coord even if sum is 0
        
        for (let l = 0; l < layers.length; l++) {
           const val = layers[l].data[j];
           if (layers[l].meta.data[j]) anyMeta = layers[l].meta.data[j];
           if (val) {
              sum += val;
              lastValidMeta = layers[l].meta.data[j];
           }
        }
        
        // Draw total on top
        if (sum > 0 && lastValidMeta) {
           ctx.textBaseline = 'bottom';
           const xPos = lastValidMeta.x;
           const yPos = chart.scales.y.getPixelForValue(sum);
           ctx.fillText(setfFmtJutaan(sum), xPos, yPos - 5);
        }
        
        // Draw bottom label (Budget / Realisasi)
        if (anyMeta && (stackId === "StackBudget" || stackId === "StackRealisasi")) {
           ctx.textBaseline = 'top';
           ctx.font = '9px sans-serif';
           ctx.fillStyle = isDark ? "#94a3b8" : "#64748b";
           let lbl = stackId === "StackBudget" ? "B" : "R";
           if (chart.canvas.id.includes("tahunan")) lbl = stackId === "StackBudget" ? "Budget" : "Realisasi";
           ctx.fillText(lbl, anyMeta.x, yBaseline + 4);
        }
      }
    }
    ctx.restore();
  }
};"""

content = re.sub(target, replacement, content, count=1, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
