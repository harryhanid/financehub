with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()
import re
match = re.search(r'const type\s*=\s*document\.getElementById\("ipay-type"\)\?\.value.*?apiFetch\(`/payment-memo/ipay/save-klaim`', text, re.DOTALL)
if match:
    print(match.group(0))
