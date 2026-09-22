import sys
sys.path.append("C:/Financehub/app")
from flask import Flask
from modules.sahabat_etf.service import get_siswa_summary

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///C:/Financehub/instance/financehub.db" # not needed if get_conn connects directly
with app.app_context():
    res = get_siswa_summary(2, [2026]) # assuming company_id=2 or 1? I don't know the company id. Let's try 1 and 2 and 3.
    print("Company 1:", [r for r in res if r["budget_total"] > 0])
    res = get_siswa_summary(2, [2026])
    print("Company 2:", [r for r in res if r["budget_total"] > 0])
