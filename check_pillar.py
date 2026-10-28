with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()
import re
match = re.search(r'_PILLAR_PA_TBL\s*=\s*{[^}]+}', text)
if match:
    print(match.group(0))
