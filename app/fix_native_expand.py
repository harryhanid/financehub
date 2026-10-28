import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "roam: 'move',",
    "roam: 'move',\n          expandAndCollapse: false,"
)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Disabled native expand/collapse to force Drill-Down paradigm and fix overlapping bug!")
