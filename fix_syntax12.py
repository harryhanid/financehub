file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(len(lines)):
    if lines[i].startswith("function setf"): print(f"{i+1}: {lines[i].strip('\n')}")
