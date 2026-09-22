import re

file_path = "C:/Financehub/app/templates/sahabat_etf/_panel.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("Budget vs Realization", "Budget vs Actual")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
