with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(tgl_final:\s*tr\._tgls\?\.\[3\]\?\.value \|\| "",)',
    r'\1\n    klasifikasi_pa: tr._klasCell?.textContent === "—" ? null : (tr._klasCell?.textContent || "Normal"),',
    text
)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
