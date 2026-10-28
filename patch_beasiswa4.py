with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(amount if route == "advance" else None\)), row\.get\("klasifikasi_pa"\) or "Normal"\)',
    r'\1, row.get("klasifikasi_pa") or "Normal")',
    text
)
# Actually the regex replacement earlier did:
# r'\1, row.get("klasifikasi_pa") or "Normal")'
# where \1 was `amount if route == "advance" else None)`
# So it produced `amount if route == "advance" else None), row.get("klasifikasi_pa") or "Normal")`

text = text.replace(
    'amount if route == "advance" else None), row.get("klasifikasi_pa") or "Normal")',
    'amount if route == "advance" else None, row.get("klasifikasi_pa") or "Normal")'
)

with open("app/modules/beasiswa/service.py", "w", encoding="utf-8") as f:
    f.write(text)
