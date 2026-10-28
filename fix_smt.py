with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# Fix VALUES line
text = re.sub(
    r'VALUES \(\?, \?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?\)""',
    r'VALUES (?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""',
    text
)

# Fix tuple line
text = re.sub(
    r'row\.get\("budget_activity"\), row\.get\("vendor"\), row\.get\("keterangan"\), _ts\(\)\)',
    r'row.get("budget_activity"), row.get("vendor"), row.get("keterangan"), klasifikasi, _ts())',
    text
)

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(text)
