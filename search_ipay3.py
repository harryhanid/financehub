with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "function ipayAddRow" in line:
        for j in range(i, min(len(lines), i+200)):
            print(f"Line {j+1}: {lines[j].rstrip()}")
            if lines[j].strip() == "}":
                if j > i + 10:
                    break
        break
