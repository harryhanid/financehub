with open("app/modules/beasiswa/routes.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.findall(r'@bp\.route\("([^"]+)"', text)
print(m)
