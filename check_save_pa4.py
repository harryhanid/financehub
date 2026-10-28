with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def save_pa_payment" in line:
        for j in range(i+60, min(len(lines), i+120)):
            if "nomor_pam" in lines[j] or "UPDATE" in lines[j] and "pa_tbl" in lines[j]:
                for k in range(j-5, j+5):
                    print(f"{k+1}: {lines[k].rstrip()}")
                break
        break
