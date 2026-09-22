import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace('" (Realisasi)"', '" (Actual)"')
content = content.replace("Realisasi</div>", "Actual</div>")
content = content.replace(">Realisasi</th>", ">Actual</th>")
content = content.replace("Draw bottom label (Budget / Realisasi)", "Draw bottom label (Budget / Actual)")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
