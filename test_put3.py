with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def edit_pam" in line or "def update_pam" in line:
        for j in range(i-2, i+15):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
