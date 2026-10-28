with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def save_klaim_payment" in line:
        for j in range(i+30, i+60):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
