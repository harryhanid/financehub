with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
print(f"Line 5436: {lines[5435].rstrip()}")
