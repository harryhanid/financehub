import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "let reqW = leaves * (260 * tz + 120) * ts;",
    "let reqW = leaves * (260 * tz + 120 * ts);"
)

with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Isolasi spacing multiplier agar hanya mengenai whitespace!")
