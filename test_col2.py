with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "colspan" in line.lower() and ("<td" in line or "td." in line):
        print(f"{i+1}: {line.strip()}")
