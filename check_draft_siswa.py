with open("app/modules/etf_payment_application/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "draft-siswa" in line:
        for j in range(i, min(i+25, len(lines))):
            print(lines[j].rstrip())
        break
