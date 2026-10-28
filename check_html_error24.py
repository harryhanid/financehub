with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(4025, 4040):
    print(f"Line {i+1}: {lines[i].rstrip()}")
