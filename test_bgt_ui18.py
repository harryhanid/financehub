with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "bgt-list-tbody" in line:
        for j in range(i-5, i+5):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
