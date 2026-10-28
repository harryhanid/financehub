with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "link.href =" in line or "etf-payment-application/attachment" in line:
        print(f"Line {i+1}: {line.strip()}")
