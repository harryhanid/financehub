with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def add_klaim_multi" in line:
        for j in range(i, min(len(lines), i+40)):
            print(f"Line {j+1}: {lines[j].rstrip()}")
        break
