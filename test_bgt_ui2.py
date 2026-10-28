with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "AddRow" in line and "bgt" in line.lower():
        for j in range(i-5, i+20):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
