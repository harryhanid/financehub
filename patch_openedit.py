with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(document\.getElementById\(\'edit-pam-no\'\)\.value\s*=\s*r\.pam_no \|\| \'\';)',
    r'\1\n  const klas = r.klasifikasi || "Normal";\n  const radio = document.querySelector(`input[name="edit-pam-klasifikasi"][value="${klas}"]`);\n  if(radio) radio.checked = true;',
    text
)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
