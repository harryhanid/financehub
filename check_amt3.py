with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'\?\.value\.replace', text)
print("Remaining ?.value.replace:", len(matches))
