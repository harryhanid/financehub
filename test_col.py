with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "11" in line and ("colspan" in line.lower() or "colspan" in line.lower()):
        print(f"{i+1}: {line.strip()}")
