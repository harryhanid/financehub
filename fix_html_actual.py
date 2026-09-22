import re

file_path = "C:/Financehub/app/templates/sahabat_etf/_panel.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Be careful not to replace 'value="realisasi"'
content = content.replace("Realisasi", "Actual")
content = content.replace("REALISASI", "ACTUAL")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
