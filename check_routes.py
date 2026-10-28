with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def open_pam_mark_complete" in line:
        for j in range(i, min(len(lines), i+30)):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
print("-" * 50)
for i, line in enumerate(lines):
    if "def update_pam_record_route" in line:
        for j in range(i, min(len(lines), i+30)):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
