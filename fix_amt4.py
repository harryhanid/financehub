with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(r'document\.getElementById\("([^"]+)"\)\?\.value\.replace\(/,/g,\s*\'\'\)', r'(document.getElementById("\1") ? document.getElementById("\1").value.replace(/,/g, "") : "")', text)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed document.getElementById optional chaining")
