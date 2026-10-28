with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
print("Line 5632 is in:", [l for l in lines[:5632] if l.startswith("function")][-1].strip())
print("Line 5721 is in:", [l for l in lines[:5721] if l.startswith("function")][-1].strip())
