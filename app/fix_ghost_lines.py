import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "treeChartInstance.setOption(option, true);",
    "treeChartInstance.clear();\n        treeChartInstance.setOption(option, true);"
)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Injected treeChartInstance.clear() to prevent ghost lines!")
