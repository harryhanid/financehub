with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "UPDATE payment_beasiswa SET pam=?," in line:
        for j in range(i-5, i+10):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
