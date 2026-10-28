with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "const btnToggle =" in line:
        for j in range(i-10, i+25):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
