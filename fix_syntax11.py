file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(600, 715):
    if "function " in lines[i]: print(f"{i+1}: {lines[i].strip('\n')}")
