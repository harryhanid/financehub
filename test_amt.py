with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(5340, 5390):
    if "tdAmt" in lines[i]:
        print(f"{i+1}: {lines[i].rstrip()}")
