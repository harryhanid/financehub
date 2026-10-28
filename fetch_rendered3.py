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
    print("Saved rendered.html")
