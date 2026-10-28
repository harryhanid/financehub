with open("app/modules/sponsorship/service.py", "r", encoding="utf-8") as f:
    text = f.read()
import re
if re.search(r'def create_transaksi_bulk', text):
    print("EXISTS")
else:
    print("MISSING")
