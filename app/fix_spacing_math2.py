import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "let reqH = (maxDepth + 1) * 450 * ts;",
    "let reqH = (maxDepth + 1) * (160 * tz + 290 * ts);"
)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Isolasi vertical spacing multiplier!")
