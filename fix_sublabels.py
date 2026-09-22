import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

plugin = """
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
            if (dataset.label === "Actual") lbl = "Act";
            if (!lbl) return;
            
            for (let j = 0; j < meta.data.length; j++) {
                if (meta.data[j]) {
                    ctx.fillText(lbl, meta.data[j].x, yBaseline + 4);
                }
            }
        }
      });
      ctx.restore();
    }
};
"""

# Insert plugin after setfStackTotalPlugin
content = content.replace("};", "};\n" + plugin, 1)

# Add plugin to setfRenderBudgetVsRealisasiChart
target = r'plugins: \[ChartDataLabels\],'
replacement = r'plugins: [ChartDataLabels, setfGroupedSublabelPlugin],'
content = re.sub(target, replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
