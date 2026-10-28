with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def get_budget(" in line:
        for j in range(i, i+30):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
