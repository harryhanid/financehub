import re

file_path = "C:/Financehub/app/templates/sahabat_etf/_panel.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("<h3>Actual per Sahabat</h3>", "<h3>Budget vs Actual per Sahabat</h3>")
content = content.replace("<h3>Actual per Sahabat (Tabel)</h3>", "<h3>Budget vs Actual per Sahabat (Tabel)</h3>")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
