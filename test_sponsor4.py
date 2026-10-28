with open("app/modules/sponsorship/routes.py", "r", encoding="utf-8") as f:
    text = f.read()
import re
for i, line in enumerate(text.split("\n")):
    if "create_transaksi_bulk" in line:
        print(f"{i+1}: {line}")
