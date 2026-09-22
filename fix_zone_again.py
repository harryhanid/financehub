import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Update setfGroupedSublabelPlugin to match "Budget (Total)"
target_label = r'if \(dataset\.label === "Budget"\) lbl = "Bgt";\n\s*if \(dataset\.label === "Actual"\) lbl = "Act";'
repl_label = """if (dataset.label && dataset.label.indexOf("Budget") === 0) lbl = "Bgt";
              if (dataset.label && dataset.label.indexOf("Actual") === 0) lbl = "Act";"""

content = re.sub(target_label, repl_label, content)

# Fix 2: Update setfTotalZonePlugin to perfectly center the xLeft
target_zone = r'const lastData = meta\.data\[meta\.data\.length - 1\];\n\s*if \(!lastData\) return;\n\s*const prevData = meta\.data\[meta\.data\.length - 2\];\n\s*const halfWidth = prevData \? \(lastData\.x - prevData\.x\) / 2 : 40;\n\s*const xLeft = lastData\.x - halfWidth \+ 10; // Give a little padding'

repl_zone = """
        let maxRightPrev = 0;
        let minLeftTotal = 99999;
        
        for (let j = 0; j < chart.data.datasets.length; j++) {
            const m = chart.getDatasetMeta(j);
            if (!m.hidden && m.data && m.data.length > 1) {
                const prevBar = m.data[m.data.length - 2];
                const lastBar = m.data[m.data.length - 1];
                if (prevBar && prevBar.x) {
                   const r = prevBar.x + (prevBar.width || 20) / 2;
                   if (r > maxRightPrev) maxRightPrev = r;
                }
                if (lastBar && lastBar.x) {
                   const l = lastBar.x - (lastBar.width || 20) / 2;
                   if (l < minLeftTotal) minLeftTotal = l;
                }
            }
        }
        
        const xLeft = maxRightPrev > 0 && minLeftTotal < 99999 ? (maxRightPrev + minLeftTotal) / 2 : chart.chartArea.left;
"""

content = re.sub(target_zone, repl_zone, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed setfGroupedSublabelPlugin and setfTotalZonePlugin!")
