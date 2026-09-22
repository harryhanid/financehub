import re
file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = r'datalabels:\s*\{[\s\S]*?formatter:\s*function.*?\}\n\s*\}'
repl = "datalabels: { display: false }"

new_content = re.sub(target, repl, content)
with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Disabled inner datalabels forcefully!")
