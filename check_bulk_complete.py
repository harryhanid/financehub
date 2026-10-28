with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def bulk_complete_pams" in line:
        for j in range(i, min(len(lines), i+80)):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
