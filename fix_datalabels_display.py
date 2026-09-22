import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add display: true to the fourth datalabels block
target = r'datalabels: \{\n\s*anchor: "end",\n\s*align: "top",\n\s*color: textColor,'
repl = """datalabels: {
                      display: true,
                      anchor: "end",
                      align: "top",
                      color: textColor,"""

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Added display: true to datalabels!")
