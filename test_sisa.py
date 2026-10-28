with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "sisa-budget" in line:
        for j in range(i-5, i+5):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
