file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(1255, 1285):
    print(f"{i+1}: {lines[i].strip('\n')}")
