with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(UPDATE payment_beasiswa SET pam=\? WHERE id IN \(\{ph\}\)",\s*)(\[pam_no\] \+ list\(payment_ids\))',
    r'UPDATE payment_beasiswa SET pam=?, klasifikasi_pam=? WHERE id IN ({ph})",\n                [pam_no, klasifikasi] + list(payment_ids)',
    text
)

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(text)
