with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def payment_memo_index" in line:
        for j in range(i-2, i+5):
            print(lines[j].rstrip())
        break
