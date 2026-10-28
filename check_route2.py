with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "@bp.route(\"/\")" in line or "@bp.route('')" in line:
        for j in range(i, i+10):
            print(lines[j].rstrip())
        break
