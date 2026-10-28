import sys
sys.path.insert(0, "app")
from app import create_app
from database import init_db
from flask_jwt_extended import create_access_token

init_db()
app = create_app(testing=True)

with app.test_client() as client:
    with app.app_context():
        # bypass login by creating token
        access_token = create_access_token(identity="admin@admin.com")
        
    client.set_cookie("fh_access", access_token)
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "admin@admin.com"
        sess["role"] = "admin"
        sess["company_code"] = "ETF"
        
    res = client.get("/payment-memo/")
    html = res.data.decode("utf-8")
    
    with open("rendered.html", "w", encoding="utf-8") as f:
        f.write(html)
