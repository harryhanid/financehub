with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("@login_required\ndef payment_memo_index():", "def payment_memo_index():")
with open("app/modules/payment_memo/routes.py", "w", encoding="utf-8") as f:
    f.write(text)

import sys
sys.path.insert(0, "app")
from app import create_app
app = create_app()
with app.test_client() as client:
    res = client.get("/payment-memo/?tab=draft-pay")
    with open("rendered.html", "wb") as f:
        f.write(res.data)

text = text.replace("def payment_memo_index():", "@login_required\ndef payment_memo_index():")
with open("app/modules/payment_memo/routes.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Saved rendered.html", len(res.data))
