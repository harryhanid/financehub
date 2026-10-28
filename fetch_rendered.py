import requests

session = requests.Session()
login_data = {
    "username": "admin",
    "password": "password"  # Need to check default password for the app or maybe skip auth?
}
# Actually I can just look at the app source to see if there's a backdoor, or just use app test client
from app import create_app
from database import init_db

init_db()
app = create_app()
with app.test_client() as client:
    # Need to simulate login or just bypass
    pass
