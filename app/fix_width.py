import re
with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "max-width: 1400px;",
    "width: 100%; box-sizing: border-box;"
)

with open("C:/Financehub/app/templates/sahabat_etf/public_index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Removed max-width constraint to make layout full-screen wide!")
