import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the plugin code
content = re.sub(r'const setfStackTotalPlugin = \{.*?\};', """const setfStackTotalPlugin = {
  id: 'customLabels',
  afterDatasetsDraw: function(chart) {
    const ctx = chart.ctx;
    ctx.save();
    
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    ctx.font = 'bold 10px sans-serif';
    ctx.fillStyle = isDark ? "#e2e8f0" : "#475569";
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    
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
    for (let stackId in metaMap) {
      const layers = metaMap[stackId];
      for (let j = 0; j < numDataPoints; j++) {
        let sum = 0;
        let lastValidMeta = null;
        for (let l = 0; l < layers.length; l++) {
           const val = layers[l].data[j];
           if (val) {
              sum += val;
              lastValidMeta = layers[l].meta.data[j];
           }
        }
        if (sum > 0 && lastValidMeta) {
           const xPos = lastValidMeta.x;
           const yPos = chart.scales.y.getPixelForValue(sum);
           ctx.fillText(setfFmtJutaan(sum), xPos, yPos - 5);
        }
      }
    }
    ctx.restore();
  }
};""", content, count=1, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
