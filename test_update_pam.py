with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def update_pam_and_application" in line:
        for j in range(i, i+50):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
