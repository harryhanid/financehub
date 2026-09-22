import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'if \(chart\.canvas\.id\.includes\("tahunan"\)\) lbl = stackId === "StackBudget" \? "Budget" : "Realisasi";'
repl = 'if (chart.canvas.id.includes("tahunan") || chart.canvas.id.includes("keluarga")) lbl = stackId === "StackBudget" ? "Bgt" : "Act";'

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated labels to Bgt and Act!")
