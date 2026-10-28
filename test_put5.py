with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "apiFetch(" in line and "pamId" in line and "edit" not in line.lower():
        print(f"{i+1}: {line.strip()}")
