with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "isMed" in line or "_isMedical" in line:
        for j in range(i-2, min(len(lines), i+15)):
            if "function" in lines[j] or "if" in lines[j] or "isMed" in lines[j]:
                print(f"Line {j+1}: {lines[j].rstrip()}")
        break
