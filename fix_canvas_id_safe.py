import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

start_str = "  setfCharts[canvasId] = new Chart(ctx, {\n    type: \"bar\",\n    data: { labels: xLabels, datasets: datasets },\n    plugins: [ChartDataLabels, customKeluargaLabelsPlugin],"

start_idx = content.find(start_str)
if start_idx != -1:
    end_str = "        y: {\n          stacked: true,\n          ticks: {\n            color: isDark ? \"#94a3b8\" : \"#64748b\",\n            callback: function (value) { return setfFmtJutaan(value); },\n          },\n          grid: { color: isDark ? \"rgba(255, 255, 255, 0.1)\" : \"rgba(0, 0, 0, 0.05)\" },\n        },\n      },\n    },\n  });"
    
    end_idx = content.find(end_str, start_idx)
    if end_idx != -1:
        print("Found exact block! Removing...")
        content = content[:start_idx] + content[end_idx + len(end_str):]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        print("Could not find end of floating block.")
else:
    print("Could not find start of floating block.")
