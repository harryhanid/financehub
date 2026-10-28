with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(r'const firstAmt = parseFloat\(siswaRow\._amt\?\.value\) \|\| 0;', r"const firstAmt = parseFloat(siswaRow._amt?.value.replace(/,/g,'')) || 0;", text)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed firstAmt parsing")
