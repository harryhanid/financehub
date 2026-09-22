import difflib

with open("C:/Financehub/pristine_sahabat.js", "r", encoding="utf-8") as f:
    pristine = f.read()

with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    current = f.read()

pristine_funcs = set()
for line in pristine.splitlines():
    if line.startswith("function "):
        pristine_funcs.add(line.split("(")[0])

current_funcs = set()
for line in current.splitlines():
    if line.startswith("function "):
        current_funcs.add(line.split("(")[0])

print("Missing functions:", pristine_funcs - current_funcs)
