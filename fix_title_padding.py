import re

file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add empty title to force spacing
target = r'plugins: \{\n\s*legend: \{'

repl = """plugins: {
                  title: { display: true, text: '', padding: { top: 0, bottom: 25 } },
                  legend: {"""

content = re.sub(target, repl, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Added title padding!")
