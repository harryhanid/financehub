with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "INSERT INTO payment_beasiswa" in line:
        for j in range(i-5, i+15):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
