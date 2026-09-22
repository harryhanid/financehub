file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("  let localLabels = labels.slice();\n  let newDatasets = [];", "  let localLabels = labels.slice();\n  localLabels.push(\"TOTAL\");\n  let newDatasets = [];")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed TOTAL push!")
