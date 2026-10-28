with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("checked\\']", "checked']")

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
