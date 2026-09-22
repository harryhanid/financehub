import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Let's replace 'backgroundColor: color,' with the pattern line
content = content.replace("backgroundColor: color,", "backgroundColor: typeof pattern !== 'undefined' ? pattern.draw(shape, color) : color,")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
