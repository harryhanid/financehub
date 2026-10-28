with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "async function ipaySaveKlaim" in line:
        for j in range(i+60, min(len(lines), i+120)):
            print(f"Line {j+1}: {lines[j].rstrip()}")
            if "}" in lines[j] and j > i+70:
                break
        break
