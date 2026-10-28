with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.search(r'def save_pa_payment.*?(?=def )', text, re.DOTALL)
if m: print(m.group(0))
