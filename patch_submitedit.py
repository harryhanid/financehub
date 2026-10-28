with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(pam_no:\s*document\.getElementById\(\'edit-pam-no\'\)\.value\.trim\(\) \|\| null,)',
    r'\1\n      klasifikasi:     document.querySelector(\'input[name="edit-pam-klasifikasi"]:checked\')?.value || "Normal",',
    text
)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
