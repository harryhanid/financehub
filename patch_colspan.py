with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = text.replace("colspan=\"10\"", "colspan=\"11\"")
text = text.replace("colSpan = 10", "colSpan = 11")

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
