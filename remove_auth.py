with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("@login_required\ndef payment_memo_index():", "def payment_memo_index():")

with open("app/modules/payment_memo/routes.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Temporarily removed login_required")
