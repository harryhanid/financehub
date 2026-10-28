with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()
import re
for match in re.finditer(r"def save_pa_payment.*", text):
    print(match.group(0))
