import sys
sys.path.append("C:/Financehub/app")
from flask import Flask
from modules.sahabat_etf.service import get_family_summary

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///C:/Financehub/instance/financehub.db"
with app.app_context():
    res = get_family_summary(2, [2026])
    print("Family Summary:", res)
