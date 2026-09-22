import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_budget = r'label: item\.name \+ " \(Budget\)",\s*data: item\.budget,\s*backgroundColor: typeof pattern !== \'undefined\' \? pattern\.draw\(shape, color\) : color,'
repl_budget = 'label: item.name + " (Budget)",\n                data: item.budget,\n                backgroundColor: color + "66",'

target_actual = r'label: item\.name \+ " \(Actual\)",\s*data: item\.realisasi,\s*backgroundColor: typeof pattern !== \'undefined\' \? pattern\.draw\(shape, color\) : color,'
repl_actual = 'label: item.name + " (Actual)",\n                data: item.realisasi,\n                backgroundColor: color,'

content = re.sub(target_budget, repl_budget, content)
content = re.sub(target_actual, repl_actual, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Removed patternomaly!")
