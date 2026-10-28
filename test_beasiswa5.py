with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.search(r'cur = conn\.execute\(\n\s*\"\"\"INSERT INTO payment_beasiswa.*?\)\)', text, re.DOTALL)
if m: print(m.group(0))
