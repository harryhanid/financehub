with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "function _ipayFillLine" in line:
        for j in range(i, i+15):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
