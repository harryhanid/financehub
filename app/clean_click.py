import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(
    r"if \(drillDownToUid\(dataCopy, targetUid\)\) \{[\s\S]*?treeChartInstance\.setOption\(\{[\s\S]*?\}\);\s*\}",
    "if (drillDownToUid(dataCopy, targetUid)) {\n            renderTree([dataCopy]);\n        }",
    content
)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Replaced click block via regex!")
