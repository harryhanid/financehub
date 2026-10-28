with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'id="table-fiori"' in line:
        for j in range(i, i+25):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
