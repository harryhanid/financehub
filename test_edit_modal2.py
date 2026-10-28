with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(1305, 1325):
    print(f"{i+1}: {lines[i].rstrip()}")
