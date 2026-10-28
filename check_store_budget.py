with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "const sisa = await _klaimFetchSiswabudget" in line:
        for j in range(max(0, i-5), min(i+15, len(lines))):
            print(lines[j].rstrip())
        break
