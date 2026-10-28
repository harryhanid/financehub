with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "save_pam" in line or "save_pam_klaim" in line or "save_pam_others" in line or "save_smt_lines_pam" in line:
        print(f"{i+1}: {line.strip()}")
