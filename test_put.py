with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "methods=[\"PUT\"]" in line and "/pam/<int:pam_id>" in lines[i-1]:
        for j in range(i-1, i+15):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
