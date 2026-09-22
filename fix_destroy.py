import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Wrap all destroy() calls in try/catch to prevent AbortError from breaking the whole page
content = content.replace("if (setfCharts[canvasId]) setfCharts[canvasId].destroy();", """try { if (setfCharts[canvasId]) setfCharts[canvasId].destroy(); } catch(e) { console.warn(e); }""")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
