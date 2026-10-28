with open("app/modules/etf_payment_application/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(SELECT l\.id AS line_id, l\.pa_id, p\.pa_number,)',
    r'\1 p.klasifikasi,',
    text
)

with open("app/modules/etf_payment_application/service.py", "w", encoding="utf-8") as f:
    f.write(text)
