import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "if (treeChartInstance) treeChartInstance.resize();\n    }",
    "}\n"
)

content = content.replace(
    "treeChartInstance.setOption(option, true);\n    } else {",
    "treeChartInstance.setOption(option, true);\n        treeChartInstance.resize();\n    } else {"
)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Moved resize() to AFTER setOption()!")
