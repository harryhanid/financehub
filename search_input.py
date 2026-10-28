with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "id=\"tab-input-payment\"" in line:
        for j in range(i, min(len(lines), i+150)):
            print(f"Line {j+1}: {lines[j].rstrip()}")
        break
