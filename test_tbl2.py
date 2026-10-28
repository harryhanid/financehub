with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
funcs = re.findall(r'async function load[A-Z_0-9]+\(', text)
print(funcs)
