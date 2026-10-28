with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.finditer(r'def insert_payment_rows', text)
for match in m:
    print(match.start())
