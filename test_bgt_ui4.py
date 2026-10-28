with open("app/templates/beasiswa/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'class="tab-btn"' in line:
        print(f"{i+1}: {line.rstrip()}")
