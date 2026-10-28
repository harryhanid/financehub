with open("app/modules/beasiswa/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "/budget/tambah" in line:
        for j in range(i, i+20):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
