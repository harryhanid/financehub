with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("@jwt_html_required\ndef index():", "def index():")
with open("app/modules/payment_memo/routes.py", "w", encoding="utf-8") as f:
    f.write(text)

import sys
sys.path.insert(0, "app")
from app import create_app
app = create_app()
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["role"] = "superadmin"
        sess["company_id"] = 1
        sess["company_code"] = "ETF"
    res = client.get("/payment-memo/?tab=draft-pay")
    with open("rendered.html", "wb") as f:
        f.write(res.data)

text = text.replace("def index():", "@jwt_html_required\ndef index():")
with open("app/modules/payment_memo/routes.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Saved rendered.html", len(res.data))
