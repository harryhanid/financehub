with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "methods=[\"PUT\"]" in line and "pam_id" in line:
        for j in range(i, i+15):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
