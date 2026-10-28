with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()
import re
if re.search(r'=/etf', text):
    print("Found more broken links")
else:
    print("No more broken links")
