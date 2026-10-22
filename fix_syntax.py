with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("link.href = /etf-payment-application/attachment/;", "link.href = '/etf-payment-application/attachment/' + id;")

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed attachment link syntax error")
