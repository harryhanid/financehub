with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "PA" in line and "Tarik" in line or "Tarik dari PA" in line:
        print(f"Line {i+1}: {line.strip()}")
