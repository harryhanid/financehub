import re
with open("C:/Financehub/app/templates/sahabat_etf/_panel.html", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("adjustSpacing(0.2)", "adjustSpacing(0.25)")
content = content.replace("adjustSpacing(-0.2)", "adjustSpacing(-0.25)")

with open("C:/Financehub/app/templates/sahabat_etf/_panel.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Increased button delta to 0.25")
