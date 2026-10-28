with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "id=\"ipay-type\"" in line:
        for j in range(i-5, min(len(lines), i+15)):
            print(f"Line {j+1}: {lines[j].rstrip()}")
        break
