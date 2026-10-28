with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(630, 680):
    print(f"Line {i+1}: {lines[i].rstrip()}")
