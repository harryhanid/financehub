with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()
import re
match = re.search(r'function ipayAddRow.*?(?=\n\n)', text, re.DOTALL)
if match:
    print(match.group(0)[:1500])
