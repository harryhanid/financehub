with open("app/modules/sponsorship/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def create_transaksi_bulk" in line:
        for j in range(i, min(len(lines), i+40)):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
