import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("title: { display: true, text: '', padding: { top: 0, bottom: 25 } },", "")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Removed title padding!")
