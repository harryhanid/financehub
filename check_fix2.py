with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for j in range(1885, 1915):
    if j < len(lines):
        print(f"{j+1}: {lines[j].rstrip()}")
