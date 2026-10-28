with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(function _ipayResetAutoFill\(tr\) \{\n\s*tr\._hidEtfLineId\.value = "";)',
    r'\1\n  if (tr._klasCell) tr._klasCell.textContent = "—";',
    text
)
text = re.sub(
    r'(tr\._hidEtfLineId\.value = line\.line_id;)',
    r'\1\n  if (tr._klasCell) tr._klasCell.textContent = line.klasifikasi || "Normal";',
    text
)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
