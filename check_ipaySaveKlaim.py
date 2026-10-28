with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "async function ipaySaveKlaim()" in line:
        for j in range(i, min(i+40, len(lines))):
            print(lines[j].rstrip())
        break
