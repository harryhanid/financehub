import sys
sys.path.insert(0, "app")
from app import create_app

app = create_app()
with app.test_client() as client:
    res = client.get("/payment-memo/?tab=draft-pay")
    with open("rendered.html", "wb") as f:
        f.write(res.data)
