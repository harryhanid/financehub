with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def update_pam_and_application" in line:
        for j in range(i, min(len(lines), i+120)):
            if "return" in lines[j] and "Berhasil" in lines[j]:
                for k in range(j-15, j+2):
                    print(f"{k+1}: {lines[k].rstrip()}")
                break
        break
