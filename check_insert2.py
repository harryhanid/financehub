with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def insert_payment_rows" in line:
        for j in range(i+60, min(len(lines), i+100)):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
