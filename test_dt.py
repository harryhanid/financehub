with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(3630, 3700):
    if "pam.status" in lines[i] or "pam.klasifikasi" in lines[i] or "td" in lines[i]:
        print(f"{i+1}: {lines[i].rstrip()}")
