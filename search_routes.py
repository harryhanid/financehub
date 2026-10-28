with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    text = f.read()
import re
for match in re.finditer(r"def .*complete.*", text):
    print(match.group(0))
for match in re.finditer(r"def .*update.*pam.*", text):
    print(match.group(0))
