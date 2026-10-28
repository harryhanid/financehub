with open("app/modules/payment_memo/routes.py", "r", encoding="utf-8") as f:
    text = f.read()
import re
for match in re.finditer(r".*update_pam_record.*", text):
    print(match.group(0))
