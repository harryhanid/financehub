with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.search(r'def insert_payment_rows.*?(?=def )', text, re.DOTALL)
if m: print(m.group(0))
