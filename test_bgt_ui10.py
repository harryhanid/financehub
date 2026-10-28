with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "function _bgtAddItemRow" in line:
        for j in range(i, i+30):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
