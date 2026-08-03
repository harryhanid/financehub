path_service = r"C:\Financehub\app\modules\sponsorship\service.py"
with open(path_service, "r", encoding="utf-8") as f:
    c = f.read()

import re
old = '"statusChart": status_chart\n    }'
new = '"statusChart": status_chart,\n        "catMix": cat_mix,\n        "yoyGrowth": yoy_growth\n    }'

c = c.replace(old, new)
with open(path_service, "w", encoding="utf-8") as f:
    f.write(c)

print("added keys")
