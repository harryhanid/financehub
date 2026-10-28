with open("app/modules/beasiswa/service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(advance_amount,status\)\n\s*VALUES \(\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\?,\'open\'\))',
    r'advance_amount,status,klasifikasi_pa)\n               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,\'open\',?)',
    text
)
text = re.sub(
    r'(amount if route == "advance" else None\))',
    r'\1, row.get("klasifikasi_pa") or "Normal")',
    text
)

with open("app/modules/beasiswa/service.py", "w", encoding="utf-8") as f:
    f.write(text)
