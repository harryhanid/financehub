with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re

# Fix all optional chaining with replace
text = re.sub(r'(\w+)\._amtInp\?\.value\.replace\(/,/g,\s*\'\'\)', r'(\1._amtInp ? \1._amtInp.value.replace(/,/g, "") : "")', text)
text = re.sub(r'(\w+)\._amt\?\.value\.replace\(/,/g,\s*\'\'\)', r'(\1._amt ? \1._amt.value.replace(/,/g, "") : "")', text)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed optional chaining with replace")
