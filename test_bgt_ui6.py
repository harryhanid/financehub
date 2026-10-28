with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "<button" in line and "udget" in line:
        print(f"{i+1}: {line.strip()}")
