with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
match = re.search(r'SELECT pam_no FROM pam_records WHERE id=\? AND company_id=\?', text)
if match:
    print("Found SELECT pam_no")
