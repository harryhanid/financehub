with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "bgt-tbody" in line or "bgtAddRow" in line:
        for j in range(i-5, i+30):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
