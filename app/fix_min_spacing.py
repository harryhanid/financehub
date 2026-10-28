import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "if (window.treeSpacingMultiplier < 0.3) window.treeSpacingMultiplier = 0.3;",
    "if (window.treeSpacingMultiplier < 0.0) window.treeSpacingMultiplier = 0.0;"
)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated minimum spacing multiplier to 0.0!")
