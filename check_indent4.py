with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(1000, 1010):
    if i < len(lines):
        print(f"Line {i+1}: {lines[i].rstrip()}")
