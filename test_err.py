with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(4090, 4130):
    print(f"{i+1}: {lines[i].rstrip()}")
