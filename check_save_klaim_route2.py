with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "/ipay/save-klaim" in line:
        for j in range(i, min(len(lines), i+30)):
            print(f"Line {j+1}: {lines[j].rstrip()}")
        break
